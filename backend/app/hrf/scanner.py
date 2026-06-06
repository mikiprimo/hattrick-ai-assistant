from datetime import datetime
from pathlib import Path
from typing import Optional
from app.hrf.parser import parse_hrf_file, _extract_filename_metadata
from app.hrf.models import HRFSnapshot


def scan_hrf_directory(
    folder_path: str,
    since_date: Optional[datetime] = None,
) -> list[HRFSnapshot]:
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"HRF folder not found: {folder_path}")

    snapshots = []
    for hrf_file in sorted(folder.glob("*.hrf")):
        try:
            _team_id, snapshot_date = _extract_filename_metadata(hrf_file.name)
        except ValueError:
            continue
        if since_date and snapshot_date <= since_date:
            continue
        try:
            snapshots.append(parse_hrf_file(str(hrf_file)))
        except Exception:
            continue

    return sorted(snapshots, key=lambda s: s.snapshot_date)
