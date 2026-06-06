import shutil
from pathlib import Path
import pytest
from app.hrf.scanner import scan_hrf_directory

FIXTURES = Path(__file__).parent / "fixtures"


def test_scan_returns_snapshots_ordered_by_date(tmp_path):
    shutil.copy(FIXTURES / "549298-2026-05-13.hrf", tmp_path)
    shutil.copy(FIXTURES / "549298-2026-05-20.hrf", tmp_path)
    snapshots = scan_hrf_directory(str(tmp_path))
    assert len(snapshots) == 2
    assert snapshots[0].snapshot_date < snapshots[1].snapshot_date


def test_scan_skips_invalid_filenames(tmp_path):
    shutil.copy(FIXTURES / "549298-2026-05-20.hrf", tmp_path)
    (tmp_path / "invalid_file.hrf").write_text("[basics]\nteamID=1\n")
    snapshots = scan_hrf_directory(str(tmp_path))
    assert len(snapshots) == 1


def test_scan_empty_folder(tmp_path):
    snapshots = scan_hrf_directory(str(tmp_path))
    assert snapshots == []


def test_scan_nonexistent_folder_raises():
    with pytest.raises(FileNotFoundError):
        scan_hrf_directory("/nonexistent/path/")


def test_scan_since_date_filters(tmp_path):
    from datetime import datetime
    shutil.copy(FIXTURES / "549298-2026-05-13.hrf", tmp_path)
    shutil.copy(FIXTURES / "549298-2026-05-20.hrf", tmp_path)
    cutoff = datetime(2026, 5, 13)
    snapshots = scan_hrf_directory(str(tmp_path), since_date=cutoff)
    assert len(snapshots) == 1
    assert snapshots[0].snapshot_date.day == 20
