"""Create a source/evidence ZIP with explicit exclusions and local secret checks."""
from pathlib import Path
import hashlib
import json
import zipfile
import subprocess

ROOT=Path(__file__).resolve().parents[1]
allowed_dirs={'backend','frontend','data','docs','scripts','verification'}
excluded_parts={'node_modules','dist','__pycache__','.pytest_cache','.pytest-tmp','.venv','.uv-cache'}
root_files={'README.md','requirements.txt','requirements-lock.txt','pytest.ini','alembic.ini','start.ps1','.env.example','.gitignore','.gitattributes'}
files=[]
tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0'))
audio_fixtures={'retrieval.wav','negation.wav','uncertainty.wav','correction.wav','browser-microphone.wav','groq-tts-accepted-trial-1-playable.wav'}
for p in ROOT.rglob('*'):
    relative=p.relative_to(ROOT)
    if relative.as_posix() not in tracked:continue
    if not p.is_file() or p.is_symlink() or any(part in excluded_parts for part in relative.parts):continue
    if len(relative.parts)==1:
        if p.name not in root_files and p.suffix not in {'.py','.mjs'}:continue
    elif relative.parts[0] not in allowed_dirs:continue
    if p.name=='.env' or (p.name.startswith('.env.') and p.name!='.env.example') or p.suffix in {'.db','.pyc','.pcm','.tsbuildinfo'} or '.db-' in p.name or p.stat().st_size==0 and p.suffix not in {'.py'}:continue
    if p.suffix=='.wav' and p.name not in audio_fixtures:continue
    files.append(p)
keys=[]
env=ROOT/'.env'
if env.exists():
    for line in env.read_text(encoding='utf-8-sig').splitlines():
        if line.startswith(('GOOGLE_API_KEY=','GROQ_API_KEY=')):
            value=line.split('=',1)[1].strip().strip('"').strip("'")
            if value:keys.append(value.encode())
for p in files:
    content=p.read_bytes()
    if any(key in content for key in keys):raise RuntimeError('Secret scan failed. Refusing to package.')
out=ROOT/'output';out.mkdir(exist_ok=True)
target=out/'viscan-dental-assistant.zip'
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for p in sorted(files):archive.write(p,arcname='viscan-dental-assistant/'+p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(target) as archive:
    assert archive.testzip() is None
    assert not any(name.endswith('/.env') or '/node_modules/' in name or '/.venv/' in name or name.endswith('.db') for name in archive.namelist())
summary={'file_count':len(files),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'checks':{'actual_api_keys_absent':True,'env_excluded':True,'runtime_database_excluded':True,'dependency_directories_excluded':True,'zip_crc_passed':True}}
(out/'package-check.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
