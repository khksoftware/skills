#!/usr/bin/env python3
"""sync_into_repo.py

Sync the skills in this folder into one or more consuming repositories, so
that both Claude Code (which discovers skills under ``.claude/skills/``) and
Codex (which discovers them under ``.agents/skills/``) can find them.

This folder is the single source-controlled master copy of these skills.
Every subdirectory here that contains a ``SKILL.md`` file is treated as one
skill and is synced by name into each target repository at:

    <target>/.claude/skills/<name>/
    <target>/.agents/skills/<name>/

For each skill/destination pair, this script:

  1. Attempts to create a real OS symlink pointing at this folder's copy of
     the skill, so the destination always reflects the source live.
  2. Falls back to a recursive copy if symlinks aren't permitted (e.g. on
     Windows without admin rights or Developer Mode enabled). A copy is a
     snapshot, not a live view — re-run this script after editing a skill
     here to refresh any copy-mode destinations.
  3. Does nothing when a destination is already correct (idempotent):
     re-running with no source changes reports "unchanged" everywhere and
     writes nothing.
  4. Cleans up destination entries for skills that this script previously
     synced but that no longer exist in the source, without touching any
     other content in the destination skills folder. This is tracked via a
     small ``.sync-manifest.json`` file this script maintains in each
     destination root — only entries recorded in that manifest are ever
     considered for removal.

Usage:
    python sync_into_repo.py --target <repo-root> [--target <repo-root> ...] [--check]

``--check`` performs a dry run: it reports what would change without writing
anything (no files created, removed, or modified; no manifest written).

Standard library only, by design — this needs to run in arbitrary consuming
projects that won't have this project's own Python environment set up.

Exit codes:
    0  success, no drift found (or --check found nothing that would change)
    1  a target directory was invalid / usage error
    2  --check found drift (something would change on a real run)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

MANIFEST_NAME = ".sync-manifest.json"
DEST_ROOTS = (
    Path(".claude") / "skills",
    Path(".agents") / "skills",
)

# Actions that do NOT count as drift for --check / exit-code purposes.
_NO_DRIFT_ACTIONS = {"unchanged", "already-absent"}


def discover_skills(source_root: Path) -> dict[str, Path]:
    """Return {skill_name: absolute_path} for every subfolder with a SKILL.md."""
    skills: dict[str, Path] = {}
    for entry in sorted(source_root.iterdir()):
        if entry.is_dir() and (entry / "SKILL.md").is_file():
            skills[entry.name] = entry.resolve()
    return skills


def hash_dir(path: Path) -> str:
    """Stable content hash of a directory (relative paths + file bytes)."""
    h = hashlib.sha256()
    if not path.is_dir():
        return ""
    for file in sorted(path.rglob("*")):
        if file.is_file():
            rel = file.relative_to(path).as_posix()
            h.update(rel.encode("utf-8"))
            h.update(file.read_bytes())
    return h.hexdigest()


def probe_symlink_support() -> bool:
    """Attempt a real symlink in a throwaway temp dir to test OS capability.

    Used only to predict outcomes in --check mode without touching the real
    target. Real (non-check) runs always attempt a genuine symlink at each
    entry regardless of this probe's result.
    """
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "src"
            src.mkdir()
            link = tmp_path / "link"
            os.symlink(src, link, target_is_directory=True)
            return True
    except (OSError, NotImplementedError):
        return False


def load_manifest(dest_root: Path) -> dict:
    manifest_path = dest_root / MANIFEST_NAME
    if manifest_path.is_file():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"entries": {}}


def save_manifest(dest_root: Path, manifest: dict) -> None:
    manifest_path = dest_root / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def sync_skill(src_path: Path, link_path: Path, symlinks_supported: bool, check: bool) -> dict:
    """Sync a single skill folder into link_path. Returns a result dict."""
    existed = link_path.exists() or link_path.is_symlink()

    # Already a correct symlink?
    if link_path.is_symlink():
        try:
            current_target = link_path.resolve()
        except OSError:
            current_target = None
        if current_target == src_path:
            return {"mode": "symlink", "action": "unchanged"}

    # Already an up-to-date copy?
    elif link_path.is_dir():
        src_hash = hash_dir(src_path)
        dest_hash = hash_dir(link_path)
        if src_hash == dest_hash:
            return {"mode": "copy", "action": "unchanged", "hash": src_hash}

    if check:
        predicted_mode = "symlink" if symlinks_supported else "copy"
        action = "would-update" if existed else "would-create"
        return {"mode": predicted_mode, "action": action}

    link_path.parent.mkdir(parents=True, exist_ok=True)
    if existed:
        _remove_path(link_path)

    try:
        os.symlink(src_path, link_path, target_is_directory=True)
        return {"mode": "symlink", "action": "updated" if existed else "created"}
    except (OSError, NotImplementedError):
        shutil.copytree(src_path, link_path)
        return {
            "mode": "copy",
            "action": "updated" if existed else "created",
            "hash": hash_dir(link_path),
        }


def remove_stale(path: Path, check: bool) -> dict:
    existed = path.exists() or path.is_symlink()
    if not existed:
        return {"action": "already-absent"}
    if check:
        return {"action": "would-remove"}
    _remove_path(path)
    return {"action": "removed"}


def sync_target(
    target: Path,
    skills: dict[str, Path],
    symlinks_supported: bool,
    check: bool,
    source_root: Path,
) -> dict:
    roots_report = []
    for dest_rel in DEST_ROOTS:
        dest_root = target / dest_rel
        manifest = load_manifest(dest_root)
        previously_managed = set(manifest.get("entries", {}).keys())

        entries_report = []
        new_entries: dict[str, dict] = {}

        for name, src_path in skills.items():
            link_path = dest_root / name
            result = sync_skill(src_path, link_path, symlinks_supported, check)
            entries_report.append({"skill": name, **result})
            new_entries[name] = {"mode": result["mode"]}

        stale_names = sorted(previously_managed - set(skills.keys()))
        for name in stale_names:
            result = remove_stale(dest_root / name, check)
            entries_report.append({"skill": name, **result})

        if not check:
            manifest["entries"] = new_entries
            manifest["source"] = str(source_root)
            save_manifest(dest_root, manifest)

        roots_report.append({"root": dest_rel.as_posix(), "entries": entries_report})

    return {"target": str(target), "roots": roots_report}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync this folder's skills into .claude/skills/ and .agents/skills/ of one or more target repos.",
    )
    parser.add_argument(
        "--target",
        dest="targets",
        action="append",
        required=True,
        metavar="REPO_ROOT",
        help="Path to a consuming repository's root. May be given multiple times.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry run: report what would change without writing anything.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    source_root = Path(__file__).resolve().parent

    skills = discover_skills(source_root)
    if not skills:
        print(f"error: no skill folders (containing SKILL.md) found under {source_root}", file=sys.stderr)
        return 1

    symlinks_supported = probe_symlink_support()

    targets_report = []
    had_invalid_target = False
    for raw_target in args.targets:
        target = Path(raw_target).resolve()
        if not target.is_dir():
            print(f"error: --target {raw_target!r} is not a directory ({target})", file=sys.stderr)
            had_invalid_target = True
            continue
        targets_report.append(sync_target(target, skills, symlinks_supported, args.check, source_root))

    drift = any(
        entry["action"] not in _NO_DRIFT_ACTIONS
        for target_report in targets_report
        for root_report in target_report["roots"]
        for entry in root_report["entries"]
    )

    report = {
        "check": args.check,
        "source": str(source_root),
        "skills": sorted(skills.keys()),
        "symlinks_supported": symlinks_supported,
        "targets": targets_report,
        "drift": drift,
    }
    print(json.dumps(report, indent=2))

    if had_invalid_target:
        return 1
    if args.check and drift:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
