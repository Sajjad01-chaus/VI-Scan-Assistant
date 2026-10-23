import copy
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from backend.app import db as store
from backend.app.config import settings
from backend.app.providers import AI
from backend.app.service import Service
import backend.app.main as main

@pytest.fixture
def client(tmp_path,monkeypatch):
    engine=store.make_engine('sqlite:///'+str(tmp_path/'test.db'))
    store.Base.metadata.create_all(engine);store.seed(engine)
    factory=sessionmaker(engine,expire_on_commit=False)
    cfg=copy.copy(settings);cfg.mode='fixture'
    ai=AI(cfg);service=Service(ai,factory)
    monkeypatch.setattr(main,'service',service)
    monkeypatch.setattr(main,'ai',ai)
    monkeypatch.setattr(store,'Session',factory)
    with TestClient(main.app) as c:yield c
    engine.dispose()

def new(client):
    r=client.post('/api/sessions',json={});assert r.status_code==200;return r.json()

def command(client,s,text,ident='u1',intent='auto'):
    r=client.post(f'/api/sessions/{s["id"]}/commands',json={'text':text,'utterance_id':ident,'context_version':s['context_version'],'intent':intent})
    assert r.status_code==200,r.text
    return r.json()

def test_correct_latest_modality_retrieval(client):
    r=command(client,new(client),"Open Priya Sharma's latest OPG report")
    assert r['kind']=='report'
    assert r['report']['id']=='RPT-001-03'
    assert r['report']['modality']=='OPG'
    assert r['evidence'][0]['quote']==r['report']['content']

def test_ambiguous_name_requires_valid_selection(client):
    r=command(client,new(client),"Open Priya's latest OPG report")
    assert r['kind']=='candidates' and len(r['candidates'])==2
    assert r['session']['report'] is None
    s=r['session']
    forged=client.post(f'/api/sessions/{s["id"]}/selection',json={'patient_id':'PT-004','context_version':s['context_version']})
    assert forged.status_code==422
    selected=client.post(f'/api/sessions/{s["id"]}/selection',json={'patient_id':'PT-002','context_version':s['context_version']}).json()
    assert selected['report']['patient_id']=='PT-002'

def test_followup_uses_selected_report_and_exact_evidence(client):
    r=command(client,new(client),"Open Priya Sharma's latest OPG report")
    answer=command(client,r['session'],'Summarize her report','u2')
    assert answer['kind']=='answer'
    assert all(e['report_id']=='RPT-001-03' for e in answer['evidence'])
    assert all(e['quote'] in r['report']['content'] for e in answer['evidence'])

def test_unresolved_switch_suspends_pronoun_followup(client):
    r=command(client,new(client),"Open Arjun Mehta's latest report")
    ambiguous=command(client,r['session'],"Open Priya's latest OPG report",'u2')
    answer=command(client,ambiguous['session'],'Summarize her report','u3')
    assert answer['kind']=='clarification' and not answer['evidence']

def test_missing_report_clears_previous_source(client):
    r=command(client,new(client),"Open Priya Sharma's latest OPG report")
    missing=command(client,r['session'],"Open Meera Iyer's latest OPG report",'u2')
    assert missing['kind']=='missing_report'
    assert missing['session']['report'] is None

def test_unsupported_claim_is_rejected(client,monkeypatch):
    async def hallucinate(_):return {'findings':[{'observation':'fracture','anatomical_site':'unspecified','polarity':'present','certainty':'asserted','evidence':'Lower right third molar is horizontally impacted.'}],'requires_clinician_review':True}
    monkeypatch.setattr(main.service.ai,'extract',hallucinate)
    r=command(client,new(client),'Lower right third molar is horizontally impacted.','u1','dictate')
    assert r['kind']=='validation' and 'Unsupported clinical claim' in r['message']
    assert 'draft' not in r

def test_uncertainty_cannot_be_removed_when_editing(client):
    s=command(client,new(client),"Open Priya Shah's latest report")['session']
    r=command(client,s,'Possible periapical radiolucency near the upper left first molar. Further assessment is required.','u2','dictate')
    draft=r['draft'];assert draft['findings'][0]['certainty']=='uncertain'
    finding={k:v for k,v in draft['findings'][0].items() if k not in ['source_span','review_flags']}
    finding['certainty']='asserted'
    bad=client.patch('/api/drafts/'+draft['id'],json={'version':draft['version'],'findings':[finding]})
    assert bad.status_code==422

def test_draft_saves_only_with_review_and_matching_patient(client):
    s=command(client,new(client),"Open Priya Sharma's latest report")['session']
    r=command(client,s,'Lower right third molar is horizontally impacted. No evidence of a fracture.','u2','dictate')
    d=r['draft'];assert d['requires_clinician_review'] is True
    saved=client.post('/api/drafts/'+d['id']+'/save',json={'version':d['version']})
    assert saved.status_code==200 and saved.json()['status']=='saved_draft'
    assert saved.json()['requires_clinician_review'] is True
    changed=command(client,r['session'],"Open Aisha Khan's latest report",'u3')
    wrong=client.post('/api/drafts/'+d['id']+'/save',json={'version':saved.json()['version']})
    assert wrong.status_code==409

def test_duplicate_utterance_replays_without_duplicate_draft(client):
    s=new(client)
    one=command(client,s,'Lower right third molar is horizontally impacted.','same','dictate')
    two=command(client,s,'Lower right third molar is horizontally impacted.','same','dictate')
    assert one['draft']['id']==two['draft']['id'] and two['replayed'] is True

def test_stale_context_is_rejected(client):
    s=new(client)
    command(client,s,"Open Priya Sharma's latest report")
    r=client.post(f'/api/sessions/{s["id"]}/commands',json={'text':'Summarize her report','utterance_id':'u2','context_version':0})
    assert r.status_code==409

def test_session_ownership_is_enforced(client):
    s=new(client);client.cookies.clear()
    assert client.get('/api/sessions/'+s['id']).status_code==404

def test_fixture_does_not_fake_unknown_dictation(client):
    r=command(client,new(client),'There is a new lesion.','u1','dictate')
    assert r['kind']=='error' and r['code']=='unsupported_fixture'

def test_no_definite_qualifier_is_preserved(client):
    r=command(client,new(client),'Upper right second molar. Correction, upper left second molar. No definite caries identified.','u1','dictate')
    assert r['draft']['findings'][0]['certainty']=='not_definite'
    assert r['draft']['findings'][0]['anatomical_site']=='upper left second molar'

def test_forged_report_citation_is_rejected(client,monkeypatch):
    async def invent(*args):return {'claims':[{'text':'Cancer','evidence':'Cancer is present.'}]}
    monkeypatch.setattr(main.service.ai,'answer',invent)
    s=command(client,new(client),"Open Priya Sharma's latest report")['session']
    r=command(client,s,'Summarize her report','u2')
    assert r['kind']=='validation' and not r['evidence']

def test_origin_check_blocks_foreign_browser_writes(client):
    r=client.post('/api/sessions',json={},headers={'origin':'https://unrelated.example'})
    assert r.status_code==403

def test_session_history_restores_commands_and_latest_draft(client):
    r=command(client,new(client),"Open Priya Sharma's latest report")
    draft=command(client,r['session'],'Lower right third molar is horizontally impacted.','u2','dictate')['draft']
    history=client.get('/api/sessions/'+r['session']['id']+'/history')
    assert history.status_code==200
    data=history.json()
    assert [m['role'] for m in data['messages']]==['user','assistant','user','assistant']
    assert data['messages'][0]['text']=="Open Priya Sharma's latest report"
    assert data['drafts'][0]['id']==draft['id']
    client.cookies.clear()
    assert client.get('/api/sessions/'+r['session']['id']+'/history').status_code==404

def test_explicit_correction_keeps_superseded_source(client):
    r=command(client,new(client),'Upper right second molar. Correction, upper left second molar. No definite caries identified.','u1','dictate')
    assert r['draft']['corrections'][0]['superseded_text']=='Upper right second molar.'
    assert r['draft']['corrections'][0]['corrected_text']=='upper left second molar'

def test_patient_reference_retrieves_only_that_patient(client):
    r=command(client,new(client),'Open PT-001 latest OPG report')
    assert r['report']['patient_id']=='PT-001'

def test_missing_extracted_identity_does_not_reuse_old_patient(client,monkeypatch):
    s=command(client,new(client),"Open Priya Sharma's latest report")['session']
    async def incomplete_plan(*args):return {'action':'retrieve','patient_name':'','modality':'OPG'}
    monkeypatch.setattr(main.service.ai,'plan',incomplete_plan)
    r=command(client,s,"Open Kavya Rao's latest OPG report",'u2')
    assert r['kind']=='clarification' and not r['evidence']
    assert not r['trace']

def test_voice_name_variant_requires_confirmation_and_blocks_old_context(client):
    old=command(client,new(client),"Open Priya Shah's report")
    result=command(client,old['session'],"Open Ayesha Khan's report",'variant')
    assert result['kind']=='candidates'
    assert [p['id'] for p in result['candidates']]==['PT-004']
    assert result['session']['patient']['id']=='PT-002'
    blocked=command(client,result['session'],'Summarize her report','blocked')
    assert blocked['kind']=='clarification' and not blocked['evidence']
    confirmed=client.post(f"/api/sessions/{old['session']['id']}/selection",json={'patient_id':'PT-004','context_version':blocked['session']['context_version']}).json()
    assert confirmed['session']['patient']['name']=='Aisha Khan'
    assert confirmed['report']['patient_id']=='PT-004'

def test_unmatched_switch_blocks_previous_report_followup(client):
    old=command(client,new(client),"Open Priya Shah's report")
    result=command(client,old['session'],"Open Unknown Person's report",'unknown')
    assert result['kind']=='clarification' and result['session']['pending']
    blocked=command(client,result['session'],'Summarize her report','blocked')
    assert blocked['kind']=='clarification' and not blocked['evidence']

def test_distant_first_name_does_not_suggest_patient(client):
    result=command(client,new(client),"Open Robert Khan's report")
    assert result['kind']=='clarification'
    assert result['session']['pending']['candidates']==[]

@pytest.mark.parametrize('reply',['Yes.','Yes, please.','Yes, that’s correct.'])
def test_single_suggestion_accepts_spoken_confirmation_without_llm(client,monkeypatch,reply):
    old=command(client,new(client),"Open Priya Shah's report")
    suggested=command(client,old['session'],"Open Ayesha Khan's CBCT report",'suggest')
    assert 'Did you mean Aisha Khan, patient PT-004?' in suggested['message']
    async def forbidden(*args):raise AssertionError('Confirmation must not require an LLM')
    monkeypatch.setattr(main.ai,'plan',forbidden)
    confirmed=command(client,suggested['session'],reply,'confirm')
    assert confirmed['report']['patient_id']=='PT-004'
    assert confirmed['report']['modality']=='CBCT'
    replay=command(client,confirmed['session'],reply,'confirm')
    assert replay['replayed'] and replay['session']['context_version']==confirmed['session']['context_version']

def test_no_rejects_suggestion_and_yes_cannot_reopen_it(client):
    suggested=command(client,new(client),"Open Ayesha Khan's report")
    rejected=command(client,suggested['session'],'No.','decline')
    assert not rejected['session']['pending']['candidates']
    confirmed=command(client,rejected['session'],'Yes.','confirm')
    assert confirmed['kind']=='clarification' and confirmed['session']['patient'] is None

def test_yes_cannot_choose_between_multiple_patients(client):
    suggested=command(client,new(client),"Open Priya's report")
    confirmed=command(client,suggested['session'],'Yes.','confirm')
    assert confirmed['kind']=='clarification' and confirmed['session']['patient'] is None

def test_seed_upgrades_only_unchanged_archived_reports(client):
    from backend.app.config import ROOT
    legacy=json.loads((ROOT/'data'/'synthetic-v1.json').read_text())
    original=next(r for r in legacy['reports'] if r['id']=='RPT-003-03')
    with store.Session.begin() as db:
        engine=db.get_bind()
        report=db.get(store.Report,original['id']);report.content=original['content'];report.version=1
        custom=db.get(store.Report,'RPT-004-03');custom.content='Locally edited synthetic report.';custom.version=1
    store.seed(engine)
    with store.Session() as db:
        upgraded=db.get(store.Report,'RPT-003-03')
        assert upgraded.version==2 and 'IMPRESSION:\n' in upgraded.content
        assert len(upgraded.content)>1200
        assert db.get(store.Report,'RPT-004-03').content=='Locally edited synthetic report.'
    store.seed(engine)
    with store.Session() as db:assert db.get(store.Report,'RPT-003-03').version==2

@pytest.mark.parametrize('reply',["It's Priya Shah.",'It’s Priya Shah.','Priya Shah','Shah','I mean Priya Shah','Select Priya Shah please','PT-002','SYNTH-0002','the first one'])
def test_pending_patient_reply_completes_original_request(client,monkeypatch,reply):
    pending=command(client,new(client),"Open Priya's latest OPG report")
    async def forbidden(*args):raise AssertionError('Explicit pending answer must not require LLM routing')
    monkeypatch.setattr(main.ai,'plan',forbidden)
    restored=client.get('/api/sessions/'+pending['session']['id']).json()
    selected=command(client,restored,reply,'reply')
    assert selected['kind']=='report' and selected['report']['id']=='RPT-002-03'
    assert selected['report']['modality']=='OPG' and selected['session']['pending'] is None
    history=client.get('/api/sessions/'+restored['id']+'/history').json()['messages']
    assert any(m['text']==reply for m in history)
    assert history[-1]['result']['report']['patient_id']=='PT-002'

@pytest.mark.parametrize('reply',['Priya','not Priya Shah','Does Priya Shah have cancer?','It is Aisha Khan'])
def test_pending_reply_does_not_select_on_ambiguous_negative_or_unrelated_text(client,reply):
    pending=command(client,new(client),"Open Priya's latest OPG report")
    result=command(client,pending['session'],reply,'reply')
    assert result['session']['pending'] and result['session']['patient'] is None
    assert 'report' not in result and not result['evidence']

def test_recent_dialogue_follows_selected_report_and_session(client,monkeypatch):
    opened=command(client,new(client),"Open Priya Shah's report")
    summarized=command(client,opened['session'],'Summarize her report','summary')
    seen=[]
    async def capture(text,report,summarize,dialogue):
        seen.extend(dialogue)
        return {'claims':[]}
    monkeypatch.setattr(main.ai,'answer',capture)
    command(client,summarized['session'],'What about that finding?','followup')
    assert any(m['text']=='Summarize her report' for m in seen)
    switched=command(client,summarized['session'],"Open Aisha Khan's report",'switch')
    seen.clear()
    command(client,switched['session'],'What about that finding?','newfollowup')
    assert not any('Priya' in m['text'] or 'Summarize her report'==m['text'] for m in seen)
    other=command(client,new(client),"Open Aisha Khan's report")
    seen.clear()
    command(client,other['session'],'What about that finding?','otherfollowup')
    assert len(seen)==2 and all('Priya' not in m['text'] for m in seen)

@pytest.mark.parametrize('misheard',['Meera Yash','Mira Yash'])
def test_misheard_first_name_and_wrong_family_offer_confirmation_then_accept_correction(client,misheard):
    result=command(client,new(client),f"Open {misheard}'s report")
    assert result['kind']=='candidates' and [p['id'] for p in result['candidates']]==['PT-006']
    assert result['session']['patient'] is None
    thanked=command(client,result['session'],'Thank you.','thanks')
    assert thanked['kind']=='acknowledgement' and thanked['session']['pending']==result['session']['pending']
    corrected=command(client,thanked['session'],'Meera Iyer','correct')
    assert corrected['report']['id']=='RPT-006-03' and corrected['session']['pending'] is None

@pytest.mark.parametrize('correction',['Meera Iyer','It’s Meera Iyer.','I mean Meera Iyer','PT-006','SYNTH-0006'])
def test_no_match_state_accepts_corrected_full_identity_without_an_open_command(client,monkeypatch,correction):
    missing=command(client,new(client),"Open Unknown Person's report")
    assert missing['kind']=='clarification' and not missing['session']['pending']['candidates']
    async def forbidden(*args):raise AssertionError('Name correction and acknowledgement must be deterministic')
    monkeypatch.setattr(main.ai,'plan',forbidden)
    thanked=command(client,missing['session'],'Thank you.','thanks')
    restored=client.get('/api/sessions/'+thanked['session']['id']).json()
    assert restored['context_version']==missing['session']['context_version']
    corrected=command(client,restored,correction,'correct')
    assert corrected['report']['id']=='RPT-006-03' and corrected['report']['modality']=='IOPA'
    assert corrected['trace'][0]['arguments']['source']=='corrected full directory identity'

def test_empty_match_correction_preserves_original_modality(client):
    missing=command(client,new(client),"Open Unknown Person's OPG report")
    corrected=command(client,missing['session'],'Meera Iyer','correct')
    assert corrected['kind']=='missing_report' and corrected['session']['report'] is None
    assert 'No OPG' in corrected['message']

@pytest.mark.parametrize('reply',['not Meera Iyer','Does Meera Iyer have cancer?','the first one','Iyer'])
def test_empty_match_recovery_does_not_guess_from_unrelated_or_partial_reply(client,reply):
    missing=command(client,new(client),"Open Unknown Person's report")
    reply=command(client,missing['session'],reply,'reply')
    assert reply['session']['pending'] and reply['session']['patient'] is None
    assert 'report' not in reply

def test_repeated_name_misrecognition_keeps_confirmation_available(client):
    suggested=command(client,new(client),"Open Mira Yash's report")
    repeated=command(client,suggested['session'],'Mira Iyer','repeat')
    assert repeated['session']['pending'] and 'Say yes or no' in repeated['message']
    confirmed=command(client,repeated['session'],'Yes.','confirm')
    assert confirmed['report']['patient_id']=='PT-006'
