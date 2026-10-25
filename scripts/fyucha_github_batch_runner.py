"""Fyucha FC GitHub Actions WordPress import batch runner."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from fyucha_cloud_checkpoint import run_git, sync_checkpoint, validate_checkpoint




def validate_import_checkpoint(feed_path, state_path):
    """Validate the saved import position and feed identity."""

    feed = Path(feed_path)
    checkpoint = Path(state_path)

    if not feed.is_file():
        raise RuntimeError("SAFETY STOP: Feed file missing")

    if not checkpoint.is_file():
        raise RuntimeError("SAFETY STOP: Checkpoint file missing")

    state = json.loads(checkpoint.read_text(encoding="utf-8"))

    offset = state.get("next_offset")
    if type(offset) is not int or offset < 0:
        raise RuntimeError("SAFETY STOP: Invalid checkpoint offset")

    expected_hash = state.get("feed_sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise RuntimeError("SAFETY STOP: Invalid feed fingerprint")

    digest = hashlib.sha256()
    with feed.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    if digest.hexdigest() != expected_hash:
        raise RuntimeError("SAFETY STOP: Feed fingerprint mismatch")

    with feed.open("rb") as stream:
        total_records = sum(1 for _ in stream)

    if offset > total_records:
        raise RuntimeError("SAFETY STOP: Offset exceeds feed length")

    return state







def synchronize_with_retry(worktree, state):
    """Retry checkpoint synchronization once after a failure."""

    try:
        return sync_checkpoint(worktree, state)
    except RuntimeError as first_error:
        print(
            "CHECKPOINT SYNC FAILED; VERIFYING AND RETRYING"
        )

        try:
            return sync_checkpoint(worktree, state)
        except RuntimeError as second_error:
            raise RuntimeError(
                "SAFETY STOP: Checkpoint synchronization failed "
                "after retry. First error: "
                f"{first_error}; Retry error: {second_error}"
            ) from second_error



def prepare_partial_checkpoint(args, previous_state):
    """Prepare safe progress after a partially failed batch."""

    current = validate_import_checkpoint(
        args.feed,
        args.state_file,
    )

    validate_checkpoint(previous_state, current)

    old_offset = previous_state["next_offset"]
    new_offset = current["next_offset"]

    if new_offset - old_offset > args.batch_size:
        raise RuntimeError(
            "SAFETY STOP: Partial batch exceeded configured size"
        )

    if current.get("status") != "FAILED":
        raise RuntimeError(
            "SAFETY STOP: Partial checkpoint is not marked FAILED"
        )

    if new_offset == old_offset:
        return None

    recovered = current.copy()
    recovered["status"] = "READY_TO_RESUME"

    return recovered



def validate_completed_batch(args, previous_state):
    """Validate checkpoint progress after an import batch."""

    current_state = validate_import_checkpoint(
        args.feed,
        args.state_file,
    )

    validate_checkpoint(previous_state, current_state)

    old_offset = previous_state["next_offset"]
    new_offset = current_state["next_offset"]

    if new_offset - old_offset > args.batch_size:
        raise RuntimeError(
            "SAFETY STOP: Batch advanced beyond configured size"
        )

    if current_state.get("status") != "READY_TO_RESUME":
        raise RuntimeError(
            "SAFETY STOP: Import batch did not finish successfully"
        )

    return current_state



def verify_remote_checkpoint(worktree):
    """Verify the checkpoint worktree is current with GitHub."""

    worktree = Path(worktree)

    branch = run_git(worktree, "branch", "--show-current")
    if branch != "import-checkpoint":
        raise RuntimeError(
            "SAFETY STOP: Wrong checkpoint branch"
        )

    status = run_git(worktree, "status", "--porcelain")
    if status:
        raise RuntimeError(
            "SAFETY STOP: Checkpoint worktree has uncommitted changes"
        )

    run_git(worktree, "fetch", "origin", "import-checkpoint")

    local_head = run_git(worktree, "rev-parse", "HEAD")
    remote_head = run_git(worktree, "rev-parse", "FETCH_HEAD")

    if local_head != remote_head:
        raise RuntimeError(
            "SAFETY STOP: Checkpoint worktree is not current"
        )

    return True



def run_importer(args):
    """Execute one WordPress import batch."""

    importer = Path(__file__).with_name(
        "wordpress_player_importer.py"
    )

    if not importer.is_file():
        raise RuntimeError(
            "SAFETY STOP: WordPress importer missing"
        )

    command = [
        sys.executable,
        str(importer),
        "--feed", args.feed,
        "--wordpress-url", args.wordpress_url,
        "--batch-size", str(args.batch_size),
        "--state-file", args.state_file,
        "--log-file", args.log_file,
        "--resume",
        "--execute",
    ]

    result = subprocess.run(
        command,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "SAFETY STOP: WordPress importer failed "
            "with exit code " + str(result.returncode)
        )

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run a Fyucha FC WordPress import batch"
    )
    parser.add_argument("--feed", required=True)
    parser.add_argument("--wordpress-url", required=True)
    parser.add_argument("--checkpoint-worktree", required=True)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--log-file", required=True)

    args = parser.parse_args()

    if not 1 <= args.batch_size <= 1000:
        parser.error("--batch-size must be between 1 and 1000")

    print("Fyucha FC GitHub Actions batch runner")

    worktree = Path(args.checkpoint_worktree)

    verify_remote_checkpoint(worktree)
    print("REMOTE CHECKPOINT VERIFICATION: PASS")

    remote_checkpoint = worktree / "checkpoint.json"

    if not remote_checkpoint.is_file():
        raise RuntimeError(
            "SAFETY STOP: Git checkpoint file missing"
        )

    saved_state = json.loads(
        remote_checkpoint.read_text(encoding="utf-8")
    )

    local_state = validate_import_checkpoint(
        args.feed,
        args.state_file,
    )

    if local_state != saved_state:
        raise RuntimeError(
            "SAFETY STOP: Local and Git checkpoints differ"
        )

    print("CHECKPOINT VALIDATION: PASS")
    print("LOCAL AND GIT CHECKPOINTS: MATCH")

    print("STARTING WORDPRESS IMPORT BATCH")

    try:
        run_importer(args)
    except RuntimeError:
        partial_state = prepare_partial_checkpoint(
            args,
            local_state,
        )

        if partial_state is not None:
            synchronize_with_retry(
                worktree,
                partial_state,
            )
            print(
                "PARTIAL PROGRESS CHECKPOINT SYNCHRONIZED"
            )
        else:
            print(
                "NO COMPLETED PLAYER PROGRESS TO SYNCHRONIZE"
            )

        raise

    print("WORDPRESS IMPORT BATCH COMPLETED")

    completed_state = validate_completed_batch(
        args,
        local_state,
    )

    print("POST-IMPORT CHECKPOINT VALIDATION: PASS")

    synchronized = synchronize_with_retry(
        worktree,
        completed_state,
    )

    print(
        "GITHUB CHECKPOINT SYNCHRONIZED: "
        + ("UPDATED" if synchronized else "UNCHANGED")
    )


if __name__ == "__main__":
    main()
