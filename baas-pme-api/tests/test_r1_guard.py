import ast
from pathlib import Path
import pytest


APPLICATION_ROOTS = {"src", "app", "constants", "database", "connectors", "controllers",
                     "dtos", "errors", "middlewares", "models", "repositories", "resources",
                     "schemas", "utils", "workers"}


def _is_application_module(module):
    return module.split(".", 1)[0] in APPLICATION_ROOTS


def check_file_for_src_imports(file_path: Path):
    """Analisa a árvore sintática (AST) de um arquivo e retorna violações de imports de src."""
    violations = []
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        violations.append((0, f"Erro ao fazer parse do arquivo {file_path}: {e}"))
        return violations

    for node in ast.walk(tree):
        # Caso 1: import src / import src.models
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_application_module(alias.name):
                    violations.append(
                        (node.lineno, f"import {alias.name}")
                    )

        # Caso 2: from src import ... / from src.utils import ...
        elif isinstance(node, ast.ImportFrom):
            if node.module and _is_application_module(node.module):
                imported_names = ", ".join(alias.name for alias in node.names)
                violations.append(
                    (node.lineno, f"from {node.module} import {imported_names}")
                )

        # Caso 3: __import__('src...')
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    if _is_application_module(node.args[0].value):
                        violations.append(
                            (node.lineno, f"__import__('{node.args[0].value}')")
                        )

    return violations


class TestR1Guardian:
    """Guardião da Regra R1: Testes NUNCA podem importar nada de `src/`.

    Nenhuma classe, enum, model, schema ou constante pode ser importada da
    aplicação para tests/. Isso não transforma SQL/subprocesso em HTTP:
    a classificação de evidências está nos marcadores do pytest.
    """

    def test_no_tests_import_from_src(self):
        tests_dir = Path(__file__).resolve().parent
        python_files = [*tests_dir.rglob("*.py"),
                        *(tests_dir.parent / "test_support").rglob("*.py")]
        assert len(python_files) > 0, "Nenhum arquivo de teste encontrado em tests/"

        all_violations = []
        for py_file in python_files:
            violations = check_file_for_src_imports(py_file)
            for line, stmt in violations:
                all_violations.append(f"[{py_file.name}:{line}] {stmt}")

        error_msg = (
            "\n[VIOLAÇÃO DA REGRA R1 DETECTADA]\n"
            "Os seguintes arquivos em tests/ estão importando código de src/:\n"
            + "\n".join(f"  • {v}" for v in all_violations)
            + "\n\nTestes devem ser 100% caixa-preta e falar apenas via HTTP/rede."
        )

        assert len(all_violations) == 0, error_msg

    def test_guardian_logic_detects_violations(self):
        """Verifica que a própria lógica do guardião detecta imports proibidos."""
        code_with_from_import = "from src.models import Account\n"
        tree1 = ast.parse(code_with_from_import)
        violations1 = []
        for node in ast.walk(tree1):
            if isinstance(node, ast.ImportFrom) and (node.module == "src" or node.module.startswith("src.")):
                violations1.append(node.module)
        assert len(violations1) == 1

        code_with_direct_import = "import src.database\n"
        tree2 = ast.parse(code_with_direct_import)
        violations2 = []
        for node in ast.walk(tree2):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "src" or alias.name.startswith("src."):
                        violations2.append(alias.name)
        assert len(violations2) == 1
