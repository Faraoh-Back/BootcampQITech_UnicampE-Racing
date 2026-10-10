"""Rastreabilidade estática de entrega; sem importar código da aplicação."""

import ast
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


PROJECT = Path(__file__).resolve().parents[1]
DOCS = PROJECT.parent / "docs"


def test_rfc_has_exact_sections_from_official_model():
    pattern = r"^#{2,3} .+$"
    expected = re.findall(pattern, (DOCS / "bootcamp-rfc-modelo.md").read_text(), re.MULTILINE)
    actual = re.findall(pattern, (DOCS / "RFC.md").read_text(), re.MULTILINE)
    assert actual == expected
    assert (DOCS / "RFC.md").read_text().count("> ## Principal desafio") == 1


def test_every_registered_product_route_is_in_rfc():
    tree = ast.parse((PROJECT / "src/app.py").read_text())
    rfc = (DOCS / "RFC.md").read_text()
    missing = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "add_api_route":
            continue
        route = node.args[0].value
        if "sample_entit" in route:
            continue
        methods = next(keyword.value for keyword in node.keywords if keyword.arg == "methods")
        for method in ast.literal_eval(methods):
            if f"| {method} | `{route}` |" not in rfc:
                missing.append((method, route))
    assert not missing, f"Rotas implementadas ausentes na RFC: {missing}"


def test_every_error_code_is_catalogued():
    code_pattern = re.compile(r"QIT\d{6}")
    documented = set(code_pattern.findall((DOCS / "DECISOES.md").read_text()))
    implemented = set()
    for source in (PROJECT / "src/errors").glob("*.py"):
        tree = ast.parse(source.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if code_pattern.fullmatch(node.value):
                    implemented.add(node.value)
    assert implemented <= documented, f"Erros sem contrato: {implemented - documented}"


def test_every_financial_domain_table_is_in_rfc_diagram():
    ddl = (PROJECT / "database/database.sql").read_text()
    tables = set(re.findall(r"CREATE TABLE\s+(\w+)", ddl, re.IGNORECASE))
    tables = {table.upper() for table in tables if not table.startswith("sample_entity")}
    rfc = (DOCS / "RFC.md").read_text()
    entities = set(re.findall(r"^\s*([A-Z_]+)\s*\{", rfc, re.MULTILINE))
    assert tables <= entities, f"Entidades entregues ausentes no DER: {tables - entities}"


def test_delivery_rfc_keeps_official_sections_and_all_product_routes():
    final = (DOCS / "entrega/RFC_FINAL.md").read_text()
    pattern = r"^#{2,3} .+$"
    expected = re.findall(pattern, (DOCS / "bootcamp-rfc-modelo.md").read_text(), re.MULTILINE)
    assert re.findall(pattern, final, re.MULTILINE) == expected
    assert final.count("> ## Principal desafio") == 1
    routes = re.findall(r"^\| (GET|POST|PUT) \| `([^`]+)`", (DOCS / "RFC.md").read_text(), re.MULTILINE)
    for method, route in routes:
        assert f"| {method} | `{route}` |" in final, (method, route)


def test_delivery_diagrams_preserve_every_entity_and_relationship():
    rfc = (DOCS / "RFC.md").read_text()
    diagrams = "\n".join(
        (DOCS / "entrega" / name).read_text()
        for name in ("der-financeiro.svg", "der-operacional.svg")
    )
    entities = set(re.findall(r"^\s*([A-Z_]+)\s*\{", rfc, re.MULTILINE))
    for entity in entities:
        assert f'data-entity="{entity}"' in diagrams
    relationships = re.findall(r'^\s*([A-Z_]+)\s+(\S+--\S+)\s+([A-Z_]+)\s*:\s*(\w+)', rfc, re.MULTILINE)
    for left, cardinality, right, label in relationships:
        assert f'data-relation="{left}:{cardinality}:{right}:{label}"' in diagrams


def test_delivery_pdfs_have_expected_pages_and_are_not_empty():
    manifest = json.loads((DOCS / "entrega/artefatos.json").read_text())
    for relative, digest in manifest["sha256"].items():
        source = (DOCS / "entrega" / relative).read_bytes()
        assert hashlib.sha256(source).hexdigest() == digest, f"Regere os PDFs: {relative} mudou"
    for name, pages in (("RFC_FINAL.pdf", 4), ("APRESENTACAO.pdf", 10)):
        pdf = (DOCS / "entrega" / name).read_bytes()
        assert pdf.startswith(b"%PDF-")
        assert len(pdf) > 20_000
        assert len(re.findall(rb"/Type\s*/Page\b", pdf)) == pages


def test_delivery_distinguishes_implemented_positive_net_from_remaining_backlog():
    for name in ("RFC_FINAL.md", "APRESENTACAO.md", "ENTREGA.md"):
        document = (DOCS / "entrega" / name).read_text()
        assert "P0.4" in document
        assert "QIT001030" in document
        assert "implementado" in document.lower()
        assert "9.5" in document
        assert "restante" in document.lower() or "demais" in document.lower()
        assert "garantias verificadas" in document.lower()
    for source in (DOCS / "RFC.md", DOCS / "entrega/RFC_FINAL.md"):
        for route in ("/account/{account_key}/credit-advance", "/account/{account_key}/quote"):
            row = next(line for line in source.read_text().splitlines()
                if line.startswith("| POST |") and f"`{route}`" in line)
            assert "422" in row and "líquido" in row, (source, route)


def _without_fenced_code(document):
    return re.sub(r"(?ms)^```[^\n]*\n.*?^```[ \t]*(?:\n|$)", "", document)


def _markdown_anchors(document):
    document = _without_fenced_code(document)
    anchors = set(re.findall(r'<[^>]+\bid=[\"\']([^\"\']+)[\"\']', document))
    seen = {}
    for heading in re.findall(r"^#{1,6}\s+(.+)$", document, re.MULTILINE):
        heading = re.sub(r"\s+#+\s*$", "", heading)
        heading = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading)
        heading = re.sub(r"<[^>]+>", "", html.unescape(heading))
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        occurrence = seen.get(slug, 0)
        anchors.add(f"{slug}-{occurrence}" if occurrence else slug)
        seen[slug] = occurrence + 1
    return anchors


def test_documentation_consolidation_keeps_canonical_sections_and_history():
    expected = {
        DOCS / "entrega/ENTREGA.md": (
            "## 6. Defesa técnica e ensaio",
            "### 6.1 Roteiro de 10 minutos",
            "### 6.2 Perguntas e respostas sustentáveis",
            "### 6.3 Registro de ensaio — preencher após realizar",
        ),
        DOCS / "PLANO_DE_EXECUCAO.md": (
            "## 13. Checkpoint histórico T3.1",
            "Data da revisão original: 2026-10-03.",
            "O marco histórico após S15 foi `143 passed`; após S21, `155 passed`.",
        ),
        DOCS / "arquivo/HISTORICO.md": (
            "## Guia de Inicialização e Setup do Ambiente (T0.1)",
            "## Como o BaaS PME é organizado",
            "## Inicialização — guia consolidado",
            "Critério de Conclusão da Tarefa T0.1",
            "não use suas instruções",
        ),
        PROJECT / "README.md": (
            "## Regras operacionais de alerta (S15)",
            "BaaSHighServerErrorRate",
            "BaaSConnectorFailures",
            "BaaSSlowDatabaseLock",
            "BaaSOutboxBacklog",
            "BaaSOutboxDeliveryFailures",
            "estes exemplos não enviam alertas sozinhos.",
        ),
    }
    for source, fragments in expected.items():
        document = source.read_text()
        for fragment in fragments:
            assert fragment in document, f"Conteúdo consolidado ausente: {source}: {fragment}"
    for relative in (
        "entrega/DEFESA.md", "CHECKPOINT_T3_1.md", "ALERTAS.md", "COMO_INICIAR.md",
        "arquivo/COMO_INICIAR_T0_1.md", "arquivo/ORGANIZACAO_API_ANTERIOR.md",
    ):
        assert not (DOCS / relative).exists(), f"Guia redundante reintroduzido: {relative}"


def test_documentation_local_links_and_markdown_anchors_resolve():
    sources = [
        *DOCS.glob("*.md"),
        *(DOCS / "arquivo").glob("*.md"),
        *(DOCS / "entrega").glob("*.md"),
        PROJECT.parent / "README.md",
        PROJECT / "README.md",
        *(PROJECT / "docs").glob("*.md"),
    ]
    missing = []
    for source in sources:
        document = _without_fenced_code(source.read_text())
        document = re.sub(r"`[^`\n]+`", "", document)
        for target in re.findall(r"!?\[[^\]\n]*\]\(([^)\n]+)\)", document):
            target = target.strip().strip("<>")
            if urlsplit(target).scheme or target.startswith("//"):
                continue  # Somente links locais: não depende de internet nem do deploy.
            path, _, fragment = target.partition("#")
            resolved = (source.parent / unquote(path)).resolve() if path else source
            if not resolved.exists():
                missing.append(f"{source.relative_to(PROJECT.parent)} -> {target}")
            elif fragment and resolved.suffix == ".md":
                if unquote(fragment) not in _markdown_anchors(resolved.read_text()):
                    missing.append(f"{source.relative_to(PROJECT.parent)} -> {target} (âncora)")
    assert not missing, "Links documentais quebrados:\n" + "\n".join(missing)
