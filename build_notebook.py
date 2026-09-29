#!/usr/bin/env python3
"""
Hand-rolled notebook builder/executor.

This sandbox has no `jupyter`/`nbformat`/`IPython` available and no general
internet access for `pip install`, so this script builds a valid nbformat-v4
.ipynb by hand and *actually executes* each code cell in a real, persistent
Python namespace (capturing stdout and the Jupyter-style "last expression"
display, including pandas' `_repr_html_`), so the committed notebook carries
genuine output -- not hand-typed fake output.

Usage: python3 build_notebook.py <out.ipynb> <through_stage:int>
Cell list (CELLS) is defined below; stages let us commit the notebook
incrementally as it's built up.
"""
import ast
import contextlib
import io
import json
import sys

NB_METADATA = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.10"},
}


def md(text):
    return {"cell_type": "markdown", "source": text}


def code(text):
    return {"cell_type": "code", "source": text}


def _make_output_from_value(value):
    outputs = []
    data = {"text/plain": repr(value)}
    if hasattr(value, "_repr_html_"):
        try:
            html = value._repr_html_()
            if html:
                data["text/html"] = html
        except Exception:
            pass
    outputs.append({
        "output_type": "execute_result",
        "data": data,
        "metadata": {},
        "execution_count": None,  # filled in by caller
    })
    return outputs


def run_code_cell(src, ns, exec_count):
    stdout_buf = io.StringIO()
    outputs = []
    tree = ast.parse(src, mode="exec")
    last_expr_node = None
    body = tree.body
    if body and isinstance(body[-1], ast.Expr):
        last_expr_node = body.pop()

    try:
        with contextlib.redirect_stdout(stdout_buf):
            exec(compile(ast.Module(body=body, type_ignores=[]), "<cell>", "exec"), ns)
            result = None
            if last_expr_node is not None:
                result = eval(
                    compile(ast.Expression(body=last_expr_node.value), "<cell>", "eval"), ns
                )
    except Exception as exc:
        stdout_val = stdout_buf.getvalue()
        if stdout_val:
            outputs.append({"output_type": "stream", "name": "stdout", "text": stdout_val})
        outputs.append({
            "output_type": "error",
            "ename": type(exc).__name__,
            "evalue": str(exc),
            "traceback": [f"{type(exc).__name__}: {exc}"],
        })
        return outputs

    stdout_val = stdout_buf.getvalue()
    if stdout_val:
        outputs.append({"output_type": "stream", "name": "stdout", "text": stdout_val})
    if last_expr_node is not None and result is not None:
        for o in _make_output_from_value(result):
            o["execution_count"] = exec_count
            outputs.append(o)
    return outputs


def build(cells, out_path):
    ns = {}
    nb_cells = []
    exec_count = 0
    for c in cells:
        src = c["source"].strip("\n")
        if c["cell_type"] == "markdown":
            nb_cells.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": src.splitlines(keepends=True),
            })
        else:
            exec_count += 1
            outputs = run_code_cell(src, ns, exec_count)
            nb_cells.append({
                "cell_type": "code",
                "metadata": {},
                "execution_count": exec_count,
                "outputs": outputs,
                "source": src.splitlines(keepends=True),
            })

    nb = {
        "cells": nb_cells,
        "metadata": NB_METADATA,
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    with open(out_path, "w") as f:
        json.dump(nb, f, indent=1)
    print(f"Wrote {out_path} with {len(nb_cells)} cells (through stage).")


if __name__ == "__main__":
    from notebook_cells import CELLS

    out_path = sys.argv[1]
    through = int(sys.argv[2]) if len(sys.argv) > 2 else len(CELLS)
    build(CELLS[:through], out_path)
