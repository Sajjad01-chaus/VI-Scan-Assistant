"""Documented, reproducible fixture demo against a running local server."""
import json
import os
import uuid
from pathlib import Path
import httpx

root=Path(__file__).resolve().parents[1]
results=[]
with httpx.Client(base_url=os.getenv('BASE_URL','http://127.0.0.1:8000'),timeout=60) as client:
    session=client.post('/api/sessions',json={}).json()
    def command(text,intent='auto'):
        global session
        body={'text':text,'intent':intent,'context_version':session['context_version'],'utterance_id':str(uuid.uuid4())}
        response=client.post('/api/sessions/'+session['id']+'/commands',json=body)
        response.raise_for_status();data=response.json();session=data['session']
        results.append({'step':len(results)+1,'request':body,'http':response.status_code,'response':data})
        print(data['kind'],':',data['message'][:120])
        return data
    result=command("Open Priya's latest OPG report")
    assert result['kind']=='candidates'
    response=client.post('/api/sessions/'+session['id']+'/selection',json={'patient_id':'PT-001','context_version':session['context_version']})
    response.raise_for_status();session=response.json()['session']
    results.append({'step':2,'request':{'patient_id':'PT-001'},'http':response.status_code,'response':response.json()})
    assert session['report']['id']=='RPT-001-03'
    command('Summarize her report')
    result=command('Possible periapical radiolucency near the upper left first molar. Further assessment is required.','dictate')
    draft=result['draft']
    bad={'observation':'fracture','anatomical_site':'unspecified','polarity':'present','certainty':'asserted','evidence':draft['source_transcript']}
    response=client.patch('/api/drafts/'+draft['id'],json={'version':draft['version'],'findings':[bad]})
    assert response.status_code==422
    results.append({'step':5,'request':'Attempt unsupported fracture edit','http':422,'response':response.json()})
    response=client.post('/api/drafts/'+draft['id']+'/save',json={'version':draft['version']})
    response.raise_for_status();results.append({'step':6,'request':'Save validated draft','http':200,'response':response.json()})
    command("Open Meera Iyer's latest OPG report")
(root/'verification'/'api-demo.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('Seven-step API demo passed; recorded verification/api-demo.json.')
