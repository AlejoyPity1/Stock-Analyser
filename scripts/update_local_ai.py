"""Install research quality controls, then analyze saved sources using local Qwen."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
REVISION = '68ff942e4066e07c067d6ba284e8a240d7c1a75e'
BASE_URL = f'https://raw.githubusercontent.com/AlejoyPity1/Stock-Analyser/{REVISION}/'
FILES = {
    'backend/app/local_ai.py': '51157d4785d94394947ab62b6f11f5e981d4f616093f0aefb734b927ecc0824f',
    'backend/app/research_quality.py': 'eb33a42985186a22dd1405f54c896ec596d8b1a132b826e31c10322e0b004eda',
    'backend/app/research.py': '85b4226ed3c205a6bfcb3f530ba723e794fd2227d2efc993f0ff0608d5c5c3ef',
    'backend/app/reporting.py': '04ca05dc43735dd6fc498f0f7e7ff4fe05e3ece0f6c582ca33254f5542377fe3',
    'scripts/diagnose_local_ai.py': '9174b73947dc2f3e6252d18770958fc006714eff856deb9385233660a453f65c',
    'scripts/reanalyze_local_ai.py': '6595c17e90ef16e2eed0e1a244018a9927fca606bf4faaf44d3a80308f868a5f',
    'frontend/app/page.tsx': 'f3d8f5673cc87605dce89045f1507ececc48beb06385228760420a146b9e167c',
    'frontend/components/ResearchFinancialFacts.tsx': '517e9328701b93126b3b92acf78b2dbbcad3c1668ecf6687f07c232e442e5083',
    'backend/app/horizon.py': '2beaa3e6dd43834cd479d21ac0bdcefdee5fe6cdafabd398a7e008a3cb503fc7',
    'frontend/components/HorizonSummary.tsx': '0e46cb014903ef37d6f7ad44598310a9dea2ede31a3585b763c6d991a25cb70b',
    'frontend/components/ResearchTimingNotice.tsx': '2b9fed8bf2da46a31f7352c72d14c2f241c13cb62881e347dbc1a1f448805189',
}


def download(url):
    request = Request(url, headers={'User-Agent': 'StockAnalyser-LocalAI-Update'})
    with urlopen(request, timeout=30) as response:
        content = response.read(1_000_001)
    if len(content) > 1_000_000:
        raise ValueError('Downloaded source exceeded the update limit.')
    return content


def install(root=ROOT, fetch=None):
    root = Path(root).resolve()
    required = ('backend/app/config.py', 'frontend/package.json', 'scripts/start.ps1')
    if not all((root / path).is_file() for path in required):
        raise ValueError('Run this script from a full Stock Analyser installation.')
    fetch = fetch or download
    verified = {}
    for relative, expected in FILES.items():
        target = root / relative
        if not target.resolve().is_relative_to(root):
            raise ValueError('Update target resolves outside the project.')
        print('Verifying ' + relative, flush=True)
        content = fetch(BASE_URL + relative)
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError('Downloaded source hash mismatch: ' + relative)
        if relative.endswith('.py'):
            compile(content, relative, 'exec')
        verified[relative] = content
    # Only the pinned code files are read/replaced. .env, stock.db, dependencies
    # and model files are never opened or rewritten by the updater.
    backup = root / '.local-ai-backups' / uuid4().hex[:12]
    backup.mkdir(parents=True)
    originals = {}
    for relative in verified:
        target = root / relative
        originals[relative] = target.exists()
        if target.exists():
            saved = backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(target.read_bytes())
    (backup / 'manifest.json').write_text(json.dumps(originals), encoding='utf-8')
    replaced = []
    with tempfile.TemporaryDirectory(prefix='.local-ai-update-', dir=root) as directory:
        try:
            for index, (relative, content) in enumerate(verified.items()):
                staged = Path(directory) / f'{index}.py'
                staged.write_bytes(content)
                os.replace(staged, root / relative)
                replaced.append(relative)
        except Exception:
            for relative in reversed(replaced):
                target = root / relative
                if originals[relative]:
                    os.replace(backup / relative, target)
                else:
                    target.unlink(missing_ok=True)
            raise
    return backup.relative_to(root).as_posix()


def restore_code(root, backup):
    root = Path(root); backup = root / backup
    originals = json.loads((backup / 'manifest.json').read_text())
    for relative, existed in originals.items():
        target = root / relative
        if existed:
            staged = target.with_name(target.name + '.restore-' + uuid4().hex[:8])
            staged.write_bytes((backup / relative).read_bytes())
            os.replace(staged, target)
        else:
            target.unlink(missing_ok=True)


def app_running():
    for port in (int(os.environ.get('WEB_PORT', '3000')), int(os.environ.get('API_PORT', '8000'))):
        with socket.socket() as connection:
            connection.settimeout(.25)
            if connection.connect_ex(('127.0.0.1', port)) == 0:
                return True
    return False


def build_frontend(root, backup):
    root = Path(root)
    current = root / 'frontend/.next'
    saved = root / backup / 'frontend-build'
    if current.is_symlink():
        raise ValueError('The frontend build directory must be local to the project.')
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not npm:
        raise RuntimeError('Node.js/npm is not available in this PowerShell window.')
    if current.exists():
        os.replace(current, saved)
    try:
        result = subprocess.run([npm, 'run', 'build'], cwd=root / 'frontend')
        if result.returncode:
            raise RuntimeError('Frontend build failed.')
    except Exception:
        if current.exists():
            shutil.rmtree(current)
        if saved.exists():
            os.replace(saved, current)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-only', action='store_true')
    parser.add_argument('--no-start', action='store_true', help='Do not launch the app after rebuilding/reanalysis.')
    args = parser.parse_args()
    if not args.install_only and app_running():
        print('Stop Stock Analyser first: press Ctrl+C in its server PowerShell window and wait for the prompt. Leave LM Studio running.', file=sys.stderr)
        raise SystemExit(1)
    try:
        backup = install()
    except Exception as error:
        print('Update failed: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
    print('Research quality update installed. Code backup: ' + backup, flush=True)
    if not args.install_only:
        try:
            print('Building the updated financial report interface.', flush=True)
            build_frontend(ROOT, backup)
        except Exception as error:
            restore_code(ROOT, backup)
            print('Build failed; previous code and build restored: ' + str(error), file=sys.stderr)
            raise SystemExit(1)
        print('Analyzing saved sources with grounded financial context.', flush=True)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/reanalyze_local_ai.py')], cwd=ROOT)
        if args.no_start:
            raise SystemExit(result.returncode)
        if result.returncode:
            print('Reanalysis needs review; inspect local-ai-reanalysis.json. Starting the app with the new guards.', flush=True)
        else:
            print('Saved-source reanalysis completed. Starting Stock Analyser.', flush=True)
        raise SystemExit(subprocess.run([sys.executable, str(ROOT / 'scripts/start.py')], cwd=ROOT).returncode)
