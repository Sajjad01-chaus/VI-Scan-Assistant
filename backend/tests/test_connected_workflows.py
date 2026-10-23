import json
import pytest
from backend.app.config import ROOT
from backend.app.service import Service
from backend.app import providers
from backend.tests.test_workflows import client,new,command
import backend.app.main as main

PATIENTS=json.loads((ROOT/'data'/'synthetic.json').read_text())['patients']
ALIASES={'PT-001':'Preeya','PT-002':'Preeya','PT-003':'Arjan','PT-004':'Aysha','PT-005':'Rohun','PT-006':'Mira'}
DICTATION='Possible periapical radiolucency near the upper left first molar. Further assessment is required.'

@pytest.mark.parametrize('patient',PATIENTS,ids=lambda p:p['id'])
@pytest.mark.parametrize('start',['unmatched','suggested','selected_other'])
@pytest.mark.parametrize('modality',['ANY','CBCT'])
def test_connected_patient_workflow(client,monkeypatch,patient,start,modality):
    async def no_external_calls(*args,**kwargs):raise AssertionError('Workflow audit must not call any cloud model')
    monkeypatch.setattr(providers,'post',no_external_calls)
    monkeypatch.setattr(main.ai,'speak',no_external_calls)
    session=new(client)
    other=next(p for p in PATIENTS if p['id']!=patient['id'])
    if start=='selected_other':session=command(client,session,f"Open {other['name']}'s report",'initial')['session']
    query='Unknown Person' if start=='unmatched' else ALIASES[patient['id']]+' Yash'
    requested='' if modality=='ANY' else modality+' '
    pending=command(client,session,f"Open {query}'s latest {requested}report",'lookup')
    assert pending['session']['pending']['modality']==modality
    assert pending['session']['patient']==session['patient']
    assert pending['session']['pending']['candidates']==[] if start=='unmatched' else patient['id'] in {p['id'] for p in pending['session']['pending']['candidates']}
    blocked=command(client,pending['session'],'Summarize her report','blocked')
    assert blocked['kind']=='clarification' and not blocked['evidence']
    thanks=command(client,blocked['session'],'Thank you.','thanks')
    assert thanks['kind']=='acknowledgement'
    assert thanks['session']['pending']==pending['session']['pending']

    monkeypatch.setattr(main,'service',Service(main.ai,main.service.factory))
    restored=client.get('/api/sessions/'+session['id']).json()
    assert restored['pending']==pending['session']['pending']
    selected=command(client,restored,"It's "+patient['name']+'.','correction')
    expected='RPT-'+patient['id'].split('-')[1]+('-03' if modality=='ANY' else '-02')
    assert selected['report']['id']==expected and selected['session']['pending'] is None
    summary=command(client,selected['session'],'Summarize her report','summary')
    assert summary['evidence'] and all(e['report_id']==expected for e in summary['evidence'])

    draft=command(client,summary['session'],DICTATION,'dictation','dictate')['draft']
    assert draft['findings'][0]['certainty']=='uncertain'
    saved=client.post('/api/drafts/'+draft['id']+'/save',json={'version':draft['version']})
    assert saved.status_code==200 and saved.json()['patient_id']==patient['id']
    history=client.get('/api/sessions/'+session['id']+'/history').json()
    assert any(m['text']=="It's "+patient['name']+'.' for m in history['messages'])
    assert any(d['id']==draft['id'] and d['status']=='saved_draft' for d in history['drafts'])

    switched=command(client,summary['session'],f"Open {other['name']}'s report",'switch')
    unsafe=client.post('/api/drafts/'+draft['id']+'/save',json={'version':saved.json()['version']})
    assert unsafe.status_code==409
    followup=command(client,switched['session'],'Summarize her report','switchedsummary')
    assert followup['evidence'] and all(e['report_id']==switched['report']['id'] for e in followup['evidence'])
    stale=client.post('/api/sessions/'+session['id']+'/commands',json={'text':'Summarize her report','utterance_id':'stale','context_version':restored['context_version'],'intent':'auto'})
    assert stale.status_code==409
    fresh=new(client)
    assert fresh['id']!=session['id'] and fresh['patient'] is None and fresh['pending'] is None
    assert client.get('/api/sessions/'+fresh['id']+'/history').json()=={'messages':[],'drafts':[]}
