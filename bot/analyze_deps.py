import ast
import json
from pathlib import Path
from collections import defaultdict


def analyze_python_dependencies(root_dir):
    dependencies = defaultdict(list)

    for py_file in Path(root_dir).rglob("*.py"):
        file_path = str(py_file)

        # Исключаем venv и другие служебные директории
        if any(
            exclude_dir in file_path
            for exclude_dir in ["venv", "__pycache__", ".venv", "env", ".env"]
        ):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            if imports:
                dependencies[str(py_file)] = imports

        except Exception as e:
            print(f"Error parsing {py_file}: {e}")

    return dependencies


if __name__ == "__main__":
    deps = analyze_python_dependencies(".")

    with open("dependencies.json", "w", encoding="utf-8") as f:
        json.dump(deps, f, indent=2, ensure_ascii=False)

    print("Анализ завершен. Результаты сохранены в dependencies.json")
