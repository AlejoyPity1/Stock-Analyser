"""The Windows handoff must preserve credentials/data and restore code on failure."""
import importlib.util
import subprocess
from types import SimpleNamespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('update_local_ai', ROOT / 'scripts/update_local_ai.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


def installation(tmp_path):
    for name in ('backend/app/config.py', 'frontend/package.json', 'scripts/start.ps1'):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('controlled fixture')
    for name in updater.FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'# original code fixture\n')
    (tmp_path / '.env').write_bytes(b'LOCAL_CONFIG_SENTINEL')
    (tmp_path / 'stock.db').write_bytes(b'LOCAL_DATABASE_SENTINEL')
    return tmp_path


def source(url):
    relative = url.removeprefix(updater.BASE_URL)
    return subprocess.run(['git', 'show', f'{updater.REVISION}:{relative}'], cwd=ROOT, check=True, capture_output=True).stdout


def test_update_verifies_every_download_before_replacing_any_code(tmp_path):
    root = installation(tmp_path)
    def corrupted(url):
        return source(url) if url == updater.BASE_URL + 'backend/app/local_ai.py' else b'# corrupt download'
    with pytest.raises(ValueError, match='hash mismatch'):
        updater.install(root, corrupted)
    assert all((root / name).read_bytes() == b'# original code fixture\n' for name in updater.FILES)
    assert (root / '.env').read_bytes() == b'LOCAL_CONFIG_SENTINEL'
    assert (root / 'stock.db').read_bytes() == b'LOCAL_DATABASE_SENTINEL'


def test_update_rolls_back_replaced_code_if_later_file_cannot_be_installed(tmp_path, monkeypatch):
    root = installation(tmp_path)
    original = updater.os.replace
    failed = False
    def replace(src, dst):
        nonlocal failed
        if Path(dst).name == 'diagnose_local_ai.py' and not failed:
            failed = True
            raise OSError('controlled installation failure')
        return original(src, dst)
    monkeypatch.setattr(updater.os, 'replace', replace)
    with pytest.raises(OSError, match='controlled installation failure'):
        updater.install(root, source)
    assert all((root / name).read_bytes() == b'# original code fixture\n' for name in updater.FILES)
    assert (root / '.env').read_bytes() == b'LOCAL_CONFIG_SENTINEL'
    assert (root / 'stock.db').read_bytes() == b'LOCAL_DATABASE_SENTINEL'


def test_failed_frontend_build_restores_old_build_and_code(tmp_path, monkeypatch):
    root = installation(tmp_path)
    (root / 'frontend/.next').mkdir()
    (root / 'frontend/.next/BUILD_ID').write_text('previous-build')
    backup = updater.install(root, source)
    monkeypatch.setattr(updater.shutil, 'which', lambda command: 'controlled-npm')
    def build(*args, **kwargs):
        (root / 'frontend/.next').mkdir()
        (root / 'frontend/.next/partial').write_text('failed-build')
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(updater.subprocess, 'run', build)
    with pytest.raises(RuntimeError, match='build failed'):
        updater.build_frontend(root, backup)
    updater.restore_code(root, backup)
    assert (root / 'frontend/.next/BUILD_ID').read_text() == 'previous-build'
    assert all((root / name).read_bytes() == b'# original code fixture\n' for name in updater.FILES)
    assert (root / '.env').read_bytes() == b'LOCAL_CONFIG_SENTINEL'
    assert (root / 'stock.db').read_bytes() == b'LOCAL_DATABASE_SENTINEL'


def test_successful_frontend_build_keeps_previous_build_in_backup(tmp_path, monkeypatch):
    root = installation(tmp_path)
    (root / 'frontend/.next').mkdir()
    (root / 'frontend/.next/BUILD_ID').write_text('previous-build')
    backup = updater.install(root, source)
    monkeypatch.setattr(updater.shutil, 'which', lambda command: 'controlled-npm')
    def build(*args, **kwargs):
        (root / 'frontend/.next').mkdir()
        (root / 'frontend/.next/BUILD_ID').write_text('new-build')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(updater.subprocess, 'run', build)
    updater.build_frontend(root, backup)
    assert (root / 'frontend/.next/BUILD_ID').read_text() == 'new-build'
    assert (root / backup / 'frontend-build/BUILD_ID').read_text() == 'previous-build'
    assert (root / '.env').read_bytes() == b'LOCAL_CONFIG_SENTINEL'
    assert (root / 'stock.db').read_bytes() == b'LOCAL_DATABASE_SENTINEL'
