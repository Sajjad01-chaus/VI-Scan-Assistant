"""Check the staged Git snapshot without printing credential values."""
from pathlib import Path
import json
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

files=git('diff','--cached','--name-only','--diff-filter=ACMR','-z').decode().split('\0')
files=[name for name in files if name]
secrets=[]
env=ROOT/'.env'
for line in (env.read_text(encoding='utf-8-sig') if env.exists() else '').splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        name,value=line.split('=',1)
        value=value.strip().strip('"').strip("'")
        if any(part in name.upper() for part in ('KEY','TOKEN','SECRET','PASSWORD')) and len(value)>=12:
            secrets.append(value.encode())
patterns=[rb'AIza[0-9A-Za-z_-]{30,}',rb'gsk_[0-9A-Za-z]{30,}',rb'gh[pousr]_[0-9A-Za-z]{30,}',rb'github_pat_[0-9A-Za-z_]{30,}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
failures=[]
total=0
for name in files:
    parts=Path(name).parts
    forbidden=any(part in {'.venv','node_modules','dist','__pycache__','.cursor','tmp','output','.uv-cache'} or part.startswith('.pytest') for part in parts)
    forbidden=forbidden or (Path(name).name.startswith('.env') and Path(name).name!='.env.example')
    forbidden=forbidden or name.endswith(('.db','.db-shm','.db-wal','.zip','.pcm','.pyc','.tsbuildinfo'))
    content=git('show',':'+name)
    total+=len(content)
    if forbidden or any(key in content for key in secrets) or any(re.search(pattern,content) for pattern in patterns):
        failures.append(name)
summary={'staged_files':len(files),'bytes':total,'failures':failures,'checks':'Staged bytes checked against local credential values, credential patterns and forbidden paths; no providers called.'}
print(json.dumps(summary,indent=2))
if not files or failures:
    raise SystemExit(1)
