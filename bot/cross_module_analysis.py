# analyze_unused.py
import ast
import json
from pathlib import Path
from collections import defaultdict


class UnusedCodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.defined_functions = set()
        self.used_functions = set()
        self.defined_classes = set()
        self.used_classes = set()

    def visit_FunctionDef(self, node):
        self.defined_functions.add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.defined_classes.add(node.name)
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_functions.add(node.id)
            self.used_classes.add(node.id)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.used_functions.add(node.func.id)
        self.generic_visit(node)


def analyze_project(root_dir):
    all_defined = defaultdict(set)
    all_used = defaultdict(set)

    for py_file in Path(root_dir).rglob("*.py"):
        if any(
            exclude in str(py_file)
            for exclude in ["venv", "__pycache__", "logs", ".venv", "env"]
        ):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            analyzer = UnusedCodeAnalyzer()
            analyzer.visit(tree)

            all_defined[str(py_file)] = analyzer.defined_functions
            all_used[str(py_file)] = analyzer.used_functions

        except SyntaxError as e:
            print(f"Syntax error in {py_file}: {e}")
        except Exception as e:
            print(f"Error analyzing {py_file}: {e}")

    return all_defined, all_used


def find_unused_functions(defined, used):
    unused = {}
    for file, functions in defined.items():
        unused_in_file = functions - used[file]
        if unused_in_file:
            # Преобразуем set в list для JSON сериализации
            unused[file] = list(unused_in_file)
    return unused


def convert_sets_to_lists(data):
    """Рекурсивно преобразует все set в list"""
    if isinstance(data, set):
        return list(data)
    elif isinstance(data, dict):
        return {k: convert_sets_to_lists(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_sets_to_lists(item) for item in data]
    else:
        return data


if __name__ == "__main__":
    defined, used = analyze_project(".")
    unused = find_unused_functions(defined, used)

    print("Неиспользуемые функции:")
    for file, functions in unused.items():
        print(f"\n{file}:")
        for func in sorted(functions):
            print(f"  - {func}")

    # Сохраняем в JSON (уже преобразовано в find_unused_functions)
    with open("unused_functions.json", "w", encoding="utf-8") as f:
        json.dump(unused, f, indent=2, ensure_ascii=False)

    # Дополнительно: сохраняем полные данные с преобразованием
    full_data = {
        "defined_functions": convert_sets_to_lists(dict(defined)),
        "used_functions": convert_sets_to_lists(dict(used)),
        "unused_functions": unused,
    }

    with open("full_analysis.json", "w", encoding="utf-8") as f:
        json.dump(full_data, f, indent=2, ensure_ascii=False)

    print(
        f"\nАнализ завершен. Найдено {sum(len(funcs) for funcs in unused.values())} неиспользуемых функций"
    )
