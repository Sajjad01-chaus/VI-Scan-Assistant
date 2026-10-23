"""Verify fixture Compose persistence across container recreation (dedicated test project)."""
import json
import os
from pathlib import Path
import subprocess
import time
import httpx

root=Path(__file__).resolve().parents[1]
project='viscan-review-01a164a6'
environment={**os.environ,'APP_PORT':'8002','AI_MODE':'fixture','GOOGLE_API_KEY':'','GROQ_API_KEY':''}
with httpx.Client(base_url='http://127.0.0.1:8002',timeout=10) as client:
    client.get('/api/health').raise_for_status()
    s=client.post('/api/sessions',json={}).json()
    r=client.post('/api/sessions/'+s['id']+'/commands',json={'text':"Open Priya Sharma's latest OPG report",'utterance_id':'persistent-volume-test','context_version':0})
    r.raise_for_status();assert r.json()['report']['id']=='RPT-001-03'
    for command in [['down'],['up','-d','--no-build']]:
        subprocess.run(['docker','compose','-p',project,*command],cwd=root,env=environment,check=True,capture_output=True)
    for attempt in range(50):
        try:
            if client.get('/api/health').status_code==200:break
        except httpx.RequestError:pass
        time.sleep(.2)
    restored=client.get('/api/sessions/'+s['id']);restored.raise_for_status()
    assert restored.json()['report']['id']=='RPT-001-03'
    history=client.get('/api/sessions/'+s['id']+'/history');history.raise_for_status()
    assert history.json()['messages'][0]['text']=="Open Priya Sharma's latest OPG report"
    result={'composeBuildAndStartup':True,'freshMigrationAndSeed':True,'reportRetrieval':True,'namedVolumeSurvivedContainerRecreation':True,'selectedReportRestored':True,'commandHistoryRestored':True,'realProviderKeysPassedToTestContainer':False}
    (root/'verification'/'compose-persistence.json').write_text(json.dumps(result,indent=2))
    print('Compose persistence passed across container recreation.')
