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


def sync(py_name: str, ipynb_name: str) -> None:
    source = notebook_source(ROOT / py_name)
    nb_path = ROOT / ipynb_name
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            cell["source"] = [line + "\n" for line in source.splitlines()]
            if cell["source"]:
                cell["source"][-1] = cell["source"][-1].rstrip("\n")
            break
    nb_path.write_text(json.dumps(nb, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Synced {ipynb_name}")


if __name__ == "__main__":
    for py_name, ipynb_name in PAIRINGS:
        sync(py_name, ipynb_name)
