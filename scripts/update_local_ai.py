"""Install the citation fix, then analyze saved sources using local Qwen."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'd15120c901206f096148528dcbaac7acba38dfa9'
BASE_URL = f'https://raw.githubusercontent.com/AlejoyPity1/Stock-Analyser/{REVISION}/'
FILES = {
    'backend/app/local_ai.py': '7150895ac8b74725479ca57f3f769b2c2009ada289cb4ad533619858077c6248',
    'scripts/diagnose_local_ai.py': '33aaea756667f439da9f07c927aa102e149b11a66b236218f1f226abc4adbd0f',
    'scripts/reanalyze_local_ai.py': '7deed813ea6f5965edef02f1f69c0c5ac3bbd88231110c77d00faafbea1f0d06',
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
        compile(content, relative, 'exec')
        verified[relative] = content
    # Only these three code files are read/replaced. .env, stock.db, dependencies
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-only', action='store_true')
    args = parser.parse_args()
    try:
        backup = install()
    except Exception as error:
        print('Update failed: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
    print('Citation update installed. Code backup: ' + backup, flush=True)
    print('The running app loads the new backend code after its next restart.', flush=True)
    if not args.install_only:
        print('Analyzing saved sources in a separate process now; the app can stay open.', flush=True)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/reanalyze_local_ai.py')], cwd=ROOT)
        raise SystemExit(result.returncode)
