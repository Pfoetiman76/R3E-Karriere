"""Regressionstests fuer die Stabilitaet der paketierten App:

1. In main.py verwendete Qt-Klassennamen muessen auch importiert sein
   (NameError wie 'QTimer is not defined' verhindern).
2. Auf Modulebene benutzte Namen muessen vorher im Modul definiert sein
   (NameError wie '_section_label is not defined' beim Import von
   karriere/widgets.py verhindern; Module mit Qt-Import werden nicht
   ausgefuehrt, daher rein statisch per AST).
"""
import ast
import builtins
import glob
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MAIN = os.path.join(os.path.dirname(__file__), "..", "main.py")
ROOT = os.path.join(os.path.dirname(__file__), "..")
_BUILTINS = set(dir(builtins)) | {"__name__", "__file__", "__doc__"}


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


class ModuleLevelNamesTest(unittest.TestCase):
    """Modulebene: Namen muessen vor ihrer Verwendung definiert sein.

    Funktions- und Klassenkoerper werden lazily ausgefuehrt und daher
    nicht geprueft; geprueft werden alle Anweisungen, die beim Import
    unmittelbar laufen (inkl. Dekoratoren und Default-Argumente).
    """

    def _refs_of_toplevel(self, node):
        """Namen, die diese Anweisung bei der Ausfuehrung benoetigt."""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            scope = list(getattr(node, "decorator_list", []))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scope += [d for d in node.args.defaults
                          if d is not None]
            refs = set()
            for part in scope:
                for n in ast.walk(part):
                    if (isinstance(n, ast.Name)
                            and isinstance(n.ctx, ast.Load)):
                        refs.add(n.id)
            return refs
        refs = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                refs.add(n.id)
        return refs

    def _defs_of_toplevel(self, node):
        """Namen, die diese Anweisung definiert."""
        out = set()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in ast.walk(node):
                if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store):
                    out.add(t.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in ast.walk(node):
                if isinstance(a, ast.alias):
                    out.add((a.asname or a.name).split(".")[0])
        return out

    def test_no_forward_references_at_module_level(self):
        files = [MAIN] + sorted(
            glob.glob(os.path.join(ROOT, "karriere", "*.py")))
        self.assertTrue(files, "Keine Quelldateien gefunden")
        for path in files:
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            defined = set()
            for node in tree.body:
                refs = self._refs_of_toplevel(node)
                missing = sorted(refs - defined - _BUILTINS)
                self.assertEqual(
                    missing, [],
                    "%s: Name(s) %s auf Modulebene verwendet, bevor sie"
                    " definiert sind" % (os.path.basename(path), missing))
                defined |= self._defs_of_toplevel(node)


if __name__ == "__main__":
    unittest.main()
