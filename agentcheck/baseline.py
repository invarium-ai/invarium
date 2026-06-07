from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from .storage import BASELINE_DIR, read_json, write_json


BASELINE_FILE = BASELINE_DIR / "latest.json"


def suite_baseline_path(suite_id: str) -> Path:
    normalized = suite_id.strip()
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", normalized).strip("._") or "suite"
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return BASELINE_DIR / f"{slug[:48]}-{digest}.json"


def save_baseline(session_data: dict, suite_id: str) -> Path:
    path = suite_baseline_path(suite_id)
    write_json(path, session_data)
    write_json(BASELINE_FILE, session_data)
    return path


def load_baseline(suite_id: str | None = None) -> dict | None:
    if suite_id:
        suite_file = suite_baseline_path(suite_id)
        if suite_file.exists():
            return read_json(suite_file)
    if not BASELINE_FILE.exists():
        return None
    legacy_data = read_json(BASELINE_FILE)
    if suite_id is None or legacy_data.get("suite_id") == suite_id:
        return legacy_data
    return None


@dataclass
class BaselineEntry:
    path: Path
    suite_id: str | None
    test_count: int
    created_at: str | None
    is_latest: bool


def list_baselines() -> list[BaselineEntry]:
    if not BASELINE_DIR.exists():
        return []
    latest_path = BASELINE_FILE.resolve() if BASELINE_FILE.exists() else None
    entries: list[BaselineEntry] = []
    for file in sorted(BASELINE_DIR.glob("*.json")):
        try:
            data = read_json(file)
        except Exception:
            continue
        reports = data.get("reports", [])
        entries.append(
            BaselineEntry(
                path=file,
                suite_id=data.get("suite_id"),
                test_count=len(reports),
                created_at=data.get("created_at"),
                is_latest=file.resolve() == latest_path,
            )
        )
    return entries


def delete_baseline(path: Path) -> None:
    path.unlink(missing_ok=True)
    if BASELINE_FILE.exists() and BASELINE_FILE.resolve() == path.resolve():
        BASELINE_FILE.unlink(missing_ok=True)


def load_baseline_from_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    return read_json(path)


def export_baseline(dest: Path) -> Path:
    if not BASELINE_FILE.exists():
        raise FileNotFoundError("No baseline found. Run `agentcheck bless` to create one.")
    data = read_json(BASELINE_FILE)
    dest.parent.mkdir(parents=True, exist_ok=True)
    write_json(dest, data)
    return dest


def import_baseline(src: Path) -> Path:
    data = read_json(src)
    if "reports" not in data:
        raise ValueError(f"Invalid baseline file: missing 'reports' key in {src}")
    suite_id = data.get("suite_id")
    if suite_id:
        suite_path = suite_baseline_path(suite_id)
        write_json(suite_path, data)
    write_json(BASELINE_FILE, data)
    return BASELINE_FILE
