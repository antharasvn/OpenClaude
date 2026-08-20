#!/usr/bin/env python3
"""
Auto-Commit Safety Net
======================
Checks for uncommitted changes in monitored repos and creates
safety-net commits. Does NOT push — local only.
"""
import subprocess
from datetime import datetime
from pathlib import Path

REPOS = [
    Path('/Users/antharas/Projects/AAAI.Studio/OS/OpenClaude'),
    Path('/Users/antharas/Projects/FFT'),
    Path('/Users/antharas/Projects/PDFScanner/PDFAI-Scanner'),
]


def run(cmd, cwd=None, timeout=300):
    # See daily_report_common.run: `git push` can hang on the network, and this
    # job fires every 10 min, so an unbounded call stacks slots.
    return subprocess.run(
        cmd, cwd=cwd, text=True, capture_output=True, check=False, timeout=timeout
    )


def auto_commit_repo(repo_path: Path) -> str:
    """Check a repo for uncommitted changes and commit if any."""
    name = repo_path.name
    if not (repo_path / '.git').exists():
        return f"  {name}: SKIP — not a git repo"

    status = run(['git', 'status', '--porcelain'], cwd=repo_path)
    if status.returncode != 0:
        return f"  {name}: ERROR — git status failed: {status.stderr.strip()}"

    if not status.stdout.strip():
        return f"  {name}: clean — nothing to commit"

    changed_lines = status.stdout.strip().split('\n')
    n_changes = len(changed_lines)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    msg = f"auto-commit safety net: {timestamp}"

    add = run(['git', 'add', '-A'], cwd=repo_path)
    if add.returncode != 0:
        return f"  {name}: ERROR — git add failed: {add.stderr.strip()}"

    commit = run(['git', 'commit', '-m', msg], cwd=repo_path)
    if commit.returncode != 0:
        return f"  {name}: ERROR — git commit failed: {commit.stderr.strip()}"

    return f"  {name}: COMMITTED — {n_changes} file(s) changed"


def main():
    print(f"Auto-commit safety net — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    for repo in REPOS:
        result = auto_commit_repo(repo)
        print(result)
    print()
    print("Done. No pushes were made.")


if __name__ == '__main__':
    main()
