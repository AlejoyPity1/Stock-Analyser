"""Local supervisor. Parse .env as data; stop only our own process trees."""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from dotenv import dotenv_values
root=Path(__file__).resolve().parents[1]
environ=os.environ.copy()
for name,value in dotenv_values(root/'.env').items():
    if value is not None:environ.setdefault(name,value)
api_port=int(environ.get('API_PORT','8000'));web_port=int(environ.get('WEB_PORT','3000'))
if not all(1024<=p<=65535 for p in (api_port,web_port)):raise SystemExit('Ports must be in range 1024..65535')
environ.setdefault('BACKEND_URL',f'http://127.0.0.1:{api_port}')
processes=[];windows=os.name=='nt'
def terminate(p,force=False):
    if p.poll() is not None:return
    try:
        if windows:subprocess.run(['taskkill','/PID',str(p.pid),'/T']+(['/F'] if force else []),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:os.killpg(p.pid,signal.SIGKILL if force else signal.SIGTERM)
    except ProcessLookupError:pass

def stop(*args):
    for p in processes:terminate(p)
    for p in processes:
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:terminate(p,force=True)
    if args:raise SystemExit(0)
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
options={'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP} if windows else {'start_new_session':True}
try:
    processes.append(subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--app-dir','backend','--host','127.0.0.1','--port',str(api_port)],cwd=root,env=environ,**options))
    processes.append(subprocess.Popen(['npm.cmd' if windows else 'npm','run','start','--','--port',str(web_port)],cwd=root/'frontend',env=environ,**options))
    while all(p.poll() is None for p in processes):time.sleep(.3)
    code=next(p.returncode for p in processes if p.returncode is not None)
finally:stop()
raise SystemExit(code)
