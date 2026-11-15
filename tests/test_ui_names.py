"""Regressionstest: In main.py verwendete Qt-Klassennamen
muessen auch importiert sein (NameError wie 'QTimer is not defined'
in der paketierten App verhindern)."""
import ast
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MAIN = os.path.join(os.path.dirname(__file__), "..", "main.py")


def _imported_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                names.add(a.asname or a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
    return names


class QtNamesTest(unittest.TestCase):
    def test_qt_names_defined(self):
        with open(MAIN, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        imported = _imported_names(tree)
        defined = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                ast.ClassDef)):
                defined.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        defined.add(t.id)
        used = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used.add(node.id)
        # Qt-Namen starten mit 'Q' (Qt-Klassen, QTimer, QColor ...)
        qt_used = {n for n in used if n.startswith("Q")}
        missing = sorted(n for n in qt_used
                         if n not in imported and n not in defined)
        self.assertEqual(missing, [],
                         "Fehlende Qt-Importe in main.py: %s" % missing)


if __name__ == "__main__":
    unittest.main()
