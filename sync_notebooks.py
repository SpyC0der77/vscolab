"""Inline extensions_install.py into notebook cells (Colab has no local imports)."""

import json
from pathlib import Path

ROOT = Path(__file__).parent
INSTALL = (ROOT / "extensions_install.py").read_text(encoding="utf-8").rstrip()
IMPORT_LINE = "from extensions_install import install_extensions\n"

PAIRINGS = [
    ("barebones.py", "vscolab.ipynb"),
    ("persistent.py", "vscolab_persistent.ipynb"),
    ("barebones_extensions.py", "vscolab_extensions.ipynb"),
    ("persistent_extensions.py", "vscolab_persistent_extensions.ipynb"),
]


def notebook_source(py_path: Path) -> str:
    source = py_path.read_text(encoding="utf-8")
    if IMPORT_LINE not in source:
        raise SystemExit(f"Missing import in {py_path}")
    source = source.replace(IMPORT_LINE, "")
    return INSTALL + "\n\n" + source.lstrip()


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
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            if cell["source"] != new_source:
                cell["source"] = new_source
                changed = True
            break
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
