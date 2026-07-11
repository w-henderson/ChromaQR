import subprocess
from pathlib import Path


def test_repository_has_no_obsolete_hosting_references():
    """Keep service-specific deployment claims out of tracked text files."""

    repository = Path(__file__).resolve().parents[1]
    tracked_files = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repository,
        check=True,
        capture_output=True
    ).stdout.split(b"\0")
    forbidden = (
        b"chromaqr." + bytes.fromhex("6865726f6b756170702e636f6d"),
        bytes.fromhex("6865726f6b75"),
    )

    matches = []
    for relative_path in tracked_files:
        if not relative_path:
            continue
        contents = (repository / relative_path.decode("utf-8")).read_bytes()
        if b"\0" in contents:
            continue
        lowered = contents.lower()
        if any(term in lowered for term in forbidden):
            matches.append(relative_path.decode("utf-8"))

    assert matches == [], "obsolete hosting references found in: {}".format(
        ", ".join(matches)
    )
