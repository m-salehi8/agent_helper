"""The core depends only on the standard library and its declared dependencies: no host-project app, no plugin."""
import ast
import sys
from pathlib import Path

from django.test import SimpleTestCase

CORE_DIR = Path(__file__).resolve().parent.parent
ALLOWED = set(sys.stdlib_module_names) | {'django', 'rest_framework', 'django_jalali', 'jdatetime', 'requests', 'agent_helper'}


def foreign_imports():
    found = []
    for path in CORE_DIR.rglob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                if name.split('.')[0] not in ALLOWED:
                    found.append(f'{path.relative_to(CORE_DIR)}:{node.lineno} {name}')
    return found


class CoreIsolationTests(SimpleTestCase):
    def test_core_imports_only_its_dependencies(self):
        self.assertEqual(foreign_imports(), [])
