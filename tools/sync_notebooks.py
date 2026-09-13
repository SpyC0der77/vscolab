"""Inline shared modules into notebook cells (Colab has no local imports)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
LIB = ROOT / "lib"
NOTEBOOKS = ROOT / "notebooks"

CONFIG_START = "# @vscolab-config\n"
CONFIG_END = "# @vscolab-config-end\n"

PARAM_TYPES = {
    "GIT_REPO": '{type:"string"}',
    "TUNNEL_NAME": '{type:"string"}',
    "VERSION": '{type:"string"}',
    "VSCOLAB_RAW": '{type:"string"}',
    "PORT": '{type:"integer"}',
    "SYNC_INTERVAL": '{type:"integer"}',
}

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
    ("standard.py", "vscolab_standard.ipynb"),
    ("standard_persistent.py", "vscolab_standard_persistent.ipynb"),
    ("ai.py", "vscolab_ai.ipynb"),
    ("ai_persistent.py", "vscolab_ai_persistent.ipynb"),
]

INTROS = {
    "vscolab_standard.ipynb": (
        "Run **Config**, then **Start**. Click the printed Open VS Code URL."
    ),
    "vscolab_standard_persistent.ipynb": (
        "Run **Config**, then **Start** (authorize Drive if asked). "
        "Click the printed Open VS Code URL."
    ),
    "vscolab_ai.ipynb": (
        "Run **Config**, then **Start**. Finish GitHub device login "
        "(`github.com/login/device`), open the printed "
        "`https://vscode.dev/tunnel/...` link, and pick **Colab AI** in Chat."
    ),
    "vscolab_ai_persistent.ipynb": (
        "Run **Config**, then **Start** (authorize Drive if asked). "
        "Finish GitHub device login (`github.com/login/device`), open the "
        "printed `https://vscode.dev/tunnel/...` link, and pick **Colab AI** in Chat."
    ),
}


def split_config(source: str) -> tuple[str, str]:
    start = source.find(CONFIG_START)
    end = source.find(CONFIG_END)
    if start == -1 or end == -1 or end < start:
        raise SystemExit(
            "Missing # @vscolab-config / # @vscolab-config-end markers."
        )
    block = source[start + len(CONFIG_START) : end].strip("\n")
    rest = (source[:start] + source[end + len(CONFIG_END) :]).lstrip("\n")
    rest = re.sub(r"\n{3,}", "\n\n", rest)
    return block, rest


def annotate_config(block: str) -> str:
    lines = ["# @title Config"]
    for line in block.splitlines():
        stripped = line.strip()
        match = re.match(r"^([A-Z_]+) = ", stripped)
        name = match.group(1) if match else None
        if (
            name in PARAM_TYPES
            and "# @param" not in line
            and not stripped.endswith("[")
            and not stripped.endswith("{")
        ):
            line = f"{line}  # @param {PARAM_TYPES[name]}"
        lines.append(line)
    return "\n".join(lines)


def inline_libs(source: str) -> str:
    prefixes: list[str] = []
    for import_line, module_name in INLINE_MODULES:
        if import_line not in source:
            continue
        source = source.replace(import_line, "")
        prefixes.append((LIB / module_name).read_text(encoding="utf-8").rstrip())
    source = source.lstrip()
    if not prefixes:
        return source
    return "\n\n".join(prefixes) + "\n\n" + source


def impl_source(script: str) -> str:
    _, rest = split_config(script)
    return "# @title Start\n" + inline_libs(rest)


def config_source(script: str) -> str:
    block, _ = split_config(script)
    return annotate_config(block)


def cell_source_lines(source: str) -> list[str]:
    lines = [line + "\n" for line in source.splitlines()]
    if lines:
        lines[-1] = lines[-1].rstrip("\n")
    return lines


def code_cell(cell_id: str, source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"id": cell_id},
        "outputs": [],
        "source": cell_source_lines(source),
    }


def markdown_cell(cell_id: str, source: str, extra_metadata: dict | None = None) -> dict:
    metadata = {"id": cell_id}
    if extra_metadata:
        metadata.update(extra_metadata)
    return {
        "cell_type": "markdown",
        "metadata": metadata,
        "source": cell_source_lines(source),
    }


def badge_cell(ipynb_name: str, existing: list[dict]) -> dict:
    if existing and existing[0]["cell_type"] == "markdown":
        return existing[0]
    url = (
        "https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/"
        f"notebooks/{ipynb_name}"
    )
    return markdown_cell(
        "view-in-github",
        f'<a href="{url}" target="_parent">'
        '<img src="https://colab.research.google.com/assets/colab-badge.svg" '
        'alt="Open In Colab"/></a>',
        extra_metadata={"colab_type": "text"},
    )


def expected_cells(py_name: str, ipynb_name: str, existing: list[dict]) -> list[dict]:
    script = (SCRIPTS / py_name).read_text(encoding="utf-8")
    return [
        badge_cell(ipynb_name, existing),
        markdown_cell("vscolab-intro", INTROS[ipynb_name]),
        code_cell("vscolab-config", config_source(script)),
        code_cell("vscolab-start", impl_source(script)),
    ]


def cell_signature(cells: list[dict]) -> list[tuple[str, str, list[str]]]:
    return [
        (c["cell_type"], c.get("metadata", {}).get("id", ""), c.get("source", []))
        for c in cells
    ]


def is_synced(py_name: str, ipynb_name: str) -> bool:
    nb_path = NOTEBOOKS / ipynb_name
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    expected = expected_cells(py_name, ipynb_name, nb["cells"])
    return cell_signature(nb["cells"]) == cell_signature(expected)


def sync(py_name: str, ipynb_name: str) -> bool:
    nb_path = NOTEBOOKS / ipynb_name
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    new_cells = expected_cells(py_name, ipynb_name, nb["cells"])
    if cell_signature(nb["cells"]) == cell_signature(new_cells):
        return False
    nb["cells"] = new_cells
    nb_path.write_text(
        json.dumps(nb, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Synced {ipynb_name}")
    return True


def check() -> None:
    stale = [ipynb for py, ipynb in PAIRINGS if not is_synced(py, ipynb)]
    if stale:
        names = ", ".join(stale)
        raise SystemExit(f"Notebooks out of sync: {names}. Run: python tools/sync_notebooks.py")


if __name__ == "__main__":
    import sys

    if "--check" in sys.argv:
        check()
        print("Notebooks are in sync.")
    else:
        for py_name, ipynb_name in PAIRINGS:
            sync(py_name, ipynb_name)
