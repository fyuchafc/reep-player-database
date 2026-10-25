"""Fyucha FC GitHub Actions checkpoint synchronization.

Remote persistence will be implemented in subsequent steps.
"""

import json
import subprocess
from pathlib import Path


def run_git(worktree, *args):
    result = subprocess.run(
        ["git", "-C", str(worktree), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Checkpoint Git operation failed: "
            + " ".join(args)
            + " (exit code " + str(result.returncode) + ")"
        )
    return result.stdout.strip()


def validate_checkpoint(previous, current):
    if previous.get("feed_sha256") != current.get("feed_sha256"):
        raise RuntimeError("SAFETY STOP: Feed fingerprint mismatch")
    old_offset = previous.get("next_offset")
    new_offset = current.get("next_offset")
    if type(old_offset) is not int or type(new_offset) is not int:
        raise RuntimeError("SAFETY STOP: Invalid checkpoint offset")
    if new_offset < old_offset:
        raise RuntimeError("SAFETY STOP: Checkpoint offset regression")
    return True

def sync_checkpoint(worktree, state):
    """Commit and push a validated checkpoint."""
    worktree = Path(worktree)

    branch = run_git(worktree, "branch", "--show-current")
    if branch != "import-checkpoint":
        raise RuntimeError("SAFETY STOP: Wrong checkpoint branch")

    run_git(worktree, "fetch", "origin", "import-checkpoint")
    local_head = run_git(worktree, "rev-parse", "HEAD")
    remote_head = run_git(worktree, "rev-parse", "FETCH_HEAD")
    if local_head != remote_head:
        ancestor = run_git(worktree, "merge-base", "HEAD", "FETCH_HEAD")
        if ancestor != remote_head:
            raise RuntimeError("SAFETY STOP: Remote checkpoint branch has changed")

        path = worktree / "checkpoint.json"
        if not path.is_file():
            raise RuntimeError("SAFETY STOP: Checkpoint file missing")

        previous = json.loads(path.read_text(encoding="utf-8"))
        validate_checkpoint(previous, state)

        if previous == state:
            run_git(worktree, "push", "origin", "import-checkpoint")
            return True

        raise RuntimeError("SAFETY STOP: Unpublished checkpoint requires recovery")

    path = worktree / "checkpoint.json"
    if not path.is_file():
        raise RuntimeError("SAFETY STOP: Checkpoint file missing")

    previous = json.loads(path.read_text(encoding="utf-8"))
    validate_checkpoint(previous, state)

    new_content = json.dumps(state, indent=2) + "\n"

    if path.read_text(encoding="utf-8") == new_content:
        return False

    path.write_text(new_content, encoding="utf-8")
    run_git(worktree, "add", "--", "checkpoint.json")
    run_git(worktree, "commit", "-m", "Update player import checkpoint")
    run_git(worktree, "push", "origin", "import-checkpoint")

    return True
