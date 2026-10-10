"""Rastreabilidade estática de entrega; sem importar código da aplicação."""

import ast
import hashlib
import json
from pathlib import Path
import re


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


def test_delivery_does_not_present_excluded_business_rule_as_implemented():
    for name in ("RFC_FINAL.md", "APRESENTACAO.md", "DEFESA.md"):
        document = (DOCS / "entrega" / name).read_text()
        assert "P0.4" in document
        assert "não implementada" in document
        assert "garantias verificadas" in document.lower()
