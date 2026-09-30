#!/usr/bin/env python3
"""
Build `ccny_calendar_scraper.ipynb` from the cell list in `notebook_cells.py`
and execute it with a real Jupyter kernel, so the committed notebook carries
genuine kernel output.

Usage: python3 build_notebook.py <out.ipynb> [through_stage:int]

`through_stage` truncates the cell list, which lets the notebook be committed
incrementally as it is built up.
"""
import sys

import nbformat
from nbclient import NotebookClient
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


def md(text):
    return ("markdown", text)


def code(text):
    return ("code", text)


def build(cells, out_path):
    nb = new_notebook(
        cells=[
            new_markdown_cell(src.strip("\n"))
            if kind == "markdown"
            else new_code_cell(src.strip("\n"))
            for kind, src in cells
        ],
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
        },
    )

    client = NotebookClient(
        nb,
        timeout=180,
        kernel_name="python3",
        allow_errors=False,
        resources={"metadata": {"path": "."}},
    )
    client.execute()

    nbformat.validate(nb)
    nbformat.write(nb, out_path)
    n_code = sum(1 for k, _ in cells if k == "code")
    print(f"Wrote {out_path}: {len(cells)} cells ({n_code} executed) ")


if __name__ == "__main__":
    from notebook_cells import CELLS

    out = sys.argv[1]
    through = int(sys.argv[2]) if len(sys.argv) > 2 else len(CELLS)
    build(CELLS[:through], out)
