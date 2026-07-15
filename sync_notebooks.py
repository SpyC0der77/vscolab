"""Inline shared modules into notebook cells (Colab has no local imports)."""

import json
from pathlib import Path

ROOT = Path(__file__).parent

# Imported helpers that must be inlined into notebook cells, in order.
INLINE_MODULES = [
    (
        "from colab_lm_bridge import setup_colab_lm\n",
        "colab_lm_bridge.py",
    ),
    (
        "from extensions_install import install_extensions\n",
        "extensions_install.py",
    ),
    (
        "from vscode_bootstrap import login_vscode, prepare_vscode, start_vscode_web\n",
        "vscode_bootstrap.py",
    ),
]

PAIRINGS = [
    ("lite.py", "vscolab_lite.ipynb"),
    ("standard.py", "vscolab_standard.ipynb"),
    ("standard_persistent.py", "vscolab_standard_persistent.ipynb"),
    ("ai.py", "vscolab_ai.ipynb"),
    ("ai_persistent.py", "vscolab_ai_persistent.ipynb"),
]


def notebook_source(py_path: Path) -> str:
    source = py_path.read_text(encoding="utf-8")
    prefixes: list[str] = []
    for import_line, module_name in INLINE_MODULES:
        if import_line not in source:
            continue
        source = source.replace(import_line, "")
        prefixes.append((ROOT / module_name).read_text(encoding="utf-8").rstrip())
    if not prefixes:
        return source
    return "\n\n".join(prefixes) + "\n\n" + source.lstrip()


def cell_source_lines(source: str) -> list[str]:
    lines = [line + "\n" for line in source.splitlines()]
    if lines:
        lines[-1] = lines[-1].rstrip("\n")
    return lines


def first_code_cell_source(nb_path: Path) -> list[str] | None:
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            return cell["source"]
    return None


def is_synced(py_name: str, ipynb_name: str) -> bool:
    expected = cell_source_lines(notebook_source(ROOT / py_name))
    actual = first_code_cell_source(ROOT / ipynb_name)
    return actual == expected


def sync(py_name: str, ipynb_name: str) -> bool:
    source = notebook_source(ROOT / py_name)
    nb_path = ROOT / ipynb_name
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    new_source = cell_source_lines(source)
    changed = False
    code_cell_found = False
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            code_cell_found = True
            if cell["source"] != new_source:
                cell["source"] = new_source
                changed = True
            break
    if not code_cell_found:
        raise SystemExit(
            f"{ipynb_name} has no code cells to synchronize. "
            "Add a code cell or run: python sync_notebooks.py"
        )
    if changed:
        nb_path.write_text(json.dumps(nb, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Synced {ipynb_name}")
    return changed


def check() -> None:
    stale = [ipynb for py, ipynb in PAIRINGS if not is_synced(py, ipynb)]
    if stale:
        names = ", ".join(stale)
        raise SystemExit(f"Notebooks out of sync: {names}. Run: python sync_notebooks.py")


if __name__ == "__main__":
    import sys

    if "--check" in sys.argv:
        check()
        print("Notebooks are in sync.")
    else:
        for py_name, ipynb_name in PAIRINGS:
            sync(py_name, ipynb_name)
