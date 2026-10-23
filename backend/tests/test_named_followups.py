import json
import pytest
from backend.app.config import ROOT
from backend.tests.test_workflows import client,new,command
import backend.app.main as main

PATIENTS=json.loads((ROOT/'data/synthetic.json').read_text())['patients']

@pytest.mark.parametrize('patient',PATIENTS,ids=lambda p:p['id'])
@pytest.mark.parametrize('model_action',['question','retrieve'])
@pytest.mark.parametrize('wording',[
    'Okay, so can you tell me what are the findings in {name}’s report?',
    'I asked what are the findings in {name}’s report.',
    'Tell me the findings in {name}’s report.',
    'Show me the findings in {name}’s report.'
])
def test_named_followup_uses_active_patient_without_reopening(client,monkeypatch,patient,model_action,wording):
    opened=command(client,new(client),f'Open {patient["name"]} report')
    original=main.ai.answer
    async def answer(text,report,*args):return await original(text,report,True,[])
    async def plan(*args):return {'action':model_action,'patient_name':patient['name'],'modality':'ANY'}
    monkeypatch.setattr(main.ai,'answer',answer)
    monkeypatch.setattr(main.ai,'plan',plan)
    result=command(client,opened['session'],wording.format(name=patient['name']),'question')
    assert result['kind']=='answer' and result['evidence']
    assert result['session']==opened['session']
    assert all(e['report_id']==opened['report']['id'] for e in result['evidence'])
    assert [t['tool'] for t in result['trace']]==['answer_from_report']


@pytest.mark.parametrize('name,allowed',[
    ('Rohan',True),('Rohan Desai',True),('Desai',True),
    ('Priya',False),('Priya Shah',False),('Unknown Person',False),
    ('Rohan Desai and Meera',False)
])
def test_named_identity_is_checked_against_directory(client,monkeypatch,name,allowed):
    opened=command(client,new(client),'Open Rohan Desai report')
    original=main.ai.answer
    async def answer(text,report,*args):return await original(text,report,True,[])
    async def plan(*args):return {'action':'question','patient_name':name,'modality':'ANY'}
    monkeypatch.setattr(main.ai,'answer',answer);monkeypatch.setattr(main.ai,'plan',plan)
    result=command(client,opened['session'],f'What are the findings in {name} report?','question')
    assert result['kind']==('answer' if allowed else 'clarification')
    assert result['session']==opened['session']
    if not allowed:assert not result['evidence'] and not result['trace']


def test_ambiguous_first_name_not_overridden_by_selected_priya(client,monkeypatch):
    opened=command(client,new(client),'Open Priya Sharma report')
    async def plan(*args):return {'action':'question','patient_name':'','modality':'ANY'}
    monkeypatch.setattr(main.ai,'plan',plan)
    result=command(client,opened['session'],'What are findings in Priya report?','question')
    assert result['kind']=='clarification' and 'ambiguous' in result['message']


def test_named_question_does_not_use_wrong_modality(client,monkeypatch):
    opened=command(client,new(client),'Open Rohan Desai OPG report')
    async def plan(*args):return {'action':'question','patient_name':'Rohan Desai','modality':'CBCT'}
    monkeypatch.setattr(main.ai,'plan',plan)
    result=command(client,opened['session'],'Tell me findings in Rohan Desai CBCT report.','question')
    assert result['kind']=='clarification' and not result['evidence']
