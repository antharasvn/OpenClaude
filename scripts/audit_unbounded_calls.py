#!/usr/bin/env python3
"""AST sweep for unbounded blocking calls.

2105z rule 2 prescribed this instrument ("an AST pass over
run/check_output/call/Popen/urlopen lacking timeout"). Taken literally it keys on
the CALLEE NAME, which is the defect rule 1 of the same entry warns about: in this
repo `run` names three unrelated things — a bounded subprocess shim, an asyncio
coroutine, and subprocess.run itself. The literal version scored 17 false positives
in 37 hits (46 %).

So this resolves the callee before judging it:
  * bare `run(...)`  -> the local `def run` in the same file; bounded if that def
    takes a `timeout` parameter, skipped entirely if it is `async def`.
  * `Popen`          -> never flagged; it does not block, so `timeout=` is not its
    bound (`.wait()`/`.communicate()` is).
  * `curl` argv      -> bounded by its own `--max-time` flag, not by `timeout=`.

Exit 1 if any unbounded site remains, so it can gate a commit.
"""
import ast
import os
import sys

ATTR_BLOCKING = {
    "subprocess": {"run", "check_output", "check_call", "call"},
    "requests": {"get", "post", "put", "delete", "patch", "head", "request"},
    "httpx": {"get", "post", "put", "delete", "patch", "head", "request"},
    "urllib": {"urlopen"},
}
BARE_BLOCKING = {"urlopen", "check_output", "check_call"}
SKIP_DIRS = {".venv", ".git", "node_modules", "workspaces", "__pycache__", "venv"}


def attr_chain(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return list(reversed(parts))


def wraps_blocking_call(node):
    """True if this def's own body makes a subprocess/urllib call.

    Without this test every local function in the repo reads as an unbounded
    wrapper (606 hits on first run). A def is a blocking wrapper because of what
    it DOES, never because of what it is missing from its signature.
    """
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call) or not isinstance(sub.func, ast.Attribute):
            continue
        chain = attr_chain(sub.func)
        if len(chain) < 2 or chain[-1] not in ATTR_BLOCKING.get(chain[0], set()):
            continue
        # A wrapper whose inner call carries its own bound is bounded, whatever
        # its signature says — boundedness is a property of the call, not the def.
        if any(k.arg == "timeout" for k in sub.keywords if k.arg):
            continue
        if curl_self_bounded(sub):
            continue
        return True
    return False


def local_run_defs(tree):
    """name -> 'bounded' | 'unbounded' | 'async' for module-level defs."""
    out = {}
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef):
            out[node.name] = "async"
        elif isinstance(node, ast.FunctionDef):
            if not wraps_blocking_call(node):
                continue                      # ordinary helper, not a shim
            names = {a.arg for a in node.args.args + node.args.kwonlyargs}
            out[node.name] = "bounded" if "timeout" in names else "unbounded"
    return out


def curl_self_bounded(node):
    """subprocess.run(['curl', ...]) carrying its own --max-time is bounded."""
    if not node.args:
        return False
    argv = node.args[0]
    if not isinstance(argv, (ast.List, ast.Tuple)):
        return False
    lits = [e.value for e in argv.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    return bool(lits) and lits[0].endswith("curl") and "--max-time" in lits


def scan(path):
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
    except SyntaxError:
        return []
    defs = local_run_defs(tree)
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            chain = attr_chain(node.func)
            if len(chain) < 2:
                continue
            root, leaf = chain[0], chain[-1]
            if leaf == "Popen" or leaf not in ATTR_BLOCKING.get(root, set()):
                continue
            name = ".".join(chain)
        elif isinstance(node.func, ast.Name):
            fname = node.func.id
            kind = defs.get(fname)
            if kind in ("async", "bounded"):
                continue                      # resolved: coroutine, or a bounded shim
            if kind == "unbounded":
                name = f"{fname}() [local shim, no timeout param]"
            elif fname in BARE_BLOCKING:
                name = fname
            else:
                continue                      # not a blocking callee we can resolve
        else:
            continue
        if any(k.arg == "timeout" for k in node.keywords if k.arg):
            continue
        if curl_self_bounded(node):
            continue
        hits.append((node.lineno, name))
    return hits


def main(root):
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            for lineno, name in scan(p):
                print(f"{os.path.relpath(p, root)}:{lineno}\t{name}(...) — no timeout=")
                total += 1
    print(f"\n{total} unbounded blocking call site(s)", file=sys.stderr)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
