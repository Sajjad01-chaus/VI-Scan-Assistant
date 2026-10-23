"""Opt-in live smoke test; sends synthetic fixtures to configured providers."""
import os
os.environ['AI_MODE']='live'
import json
import time
import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app

root=Path(__file__).resolve().parents[1]
results=[]
with TestClient(app) as client:
    session=client.post('/api/sessions',json={}).json()
    def command(text,intent='auto'):
        global session
        start=time.perf_counter()
        r=client.post('/api/sessions/'+session['id']+'/commands',json={'text':text,'intent':intent,'context_version':session['context_version'],'utterance_id':str(uuid.uuid4())})
        r.raise_for_status();data=r.json();session=data['session']
        results.append({'request':text,'elapsed_ms':round((time.perf_counter()-start)*1000),'response':data})
        print(data['kind'],':',data['message'][:160])
        return data
    ambiguous=command("Open Priya's latest OPG report")
    assert ambiguous['kind']=='candidates',ambiguous['message']
    r=client.post('/api/sessions/'+session['id']+'/selection',json={'patient_id':'PT-001','context_version':session['context_version']});r.raise_for_status();session=r.json()['session']
    results.append({'request':'Select PT-001','response':r.json()})
    summary=command('Summarize her report')
    assert summary['kind']=='answer' and summary['evidence']
    draft=command('Possible periapical radiolucency near the upper left first molar. Further assessment is required.','dictate')
    assert draft['kind']=='draft',draft['message']
    assert draft['draft']['findings'][0]['certainty']=='uncertain'
    unsupported=command('Does this report confirm oral cancer?')
    assert unsupported['kind']=='answer' and not unsupported['evidence'],unsupported
    speech=client.post('/api/sessions/'+session['id']+'/speech',json={'turn_id':summary['turn_id']})
    speech.raise_for_status()
    (root/'verification'/'app-live-speech.wav').write_bytes(speech.content)
    results.append({'task':'speech','http':speech.status_code,'bytes':len(speech.content),'provider':speech.headers.get('x-speech-provider')})
(root/'verification'/'app-live-smoke.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('Live application smoke passed: ambiguity, selection, grounded follow-up, uncertain draft, unsupported question, TTS.')
