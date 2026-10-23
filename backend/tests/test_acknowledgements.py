import pytest
from backend.tests.test_workflows import client,new,command
from backend.app.service import acknowledgement
import backend.app.main as main


@pytest.mark.parametrize('text',[
    'Okay, thanks.', 'OK thanks!', 'Okay, thank you.', 'Thanks, got it.',
    'Alright, thanks a lot.', 'Got it. Thank you very much.',
    'Perfect, thank you so much.', 'Thank you for your help.',
    'Great, understood.', 'Sounds good. That’s all.'
])
@pytest.mark.parametrize('state',['empty','selected','pending','draft'])
def test_polite_closing_never_needs_a_provider_or_changes_context(client,monkeypatch,text,state):
    session=new(client)
    if state in {'selected','draft'}:session=command(client,session,'Open Priya Sharma report')['session']
    if state=='pending':session=command(client,session,'Open Priya report')['session']
    if state=='draft':
        draft=command(client,session,'Lower right third molar is horizontally impacted.','draft','dictate')['draft']
    async def forbidden(*args,**kwargs):raise AssertionError('Polite closing must not call any provider')
    for method in ['plan','answer','extract','interpret_identity_reply','speak']:monkeypatch.setattr(main.ai,method,forbidden)
    result=command(client,session,text,'closing')
    assert result['kind']=='acknowledgement' and result['session']==session
    assert not result['trace'] and not result['evidence']
    if state=='pending':assert 'still have your report request' in result['message']
    if state=='draft':assert client.get('/api/drafts/'+draft['id']).json()['version']==draft['version']


@pytest.mark.parametrize('text',[
    'Okay thanks, summarize her report.', 'Thanks, what are the findings?',
    'Okay, open Meera Iyer report.', 'No thanks.', 'Okay, it is Priya Shah.',
    'Thank you. She has pain.', 'Not okay.', 'Thanks for nothing.'
])
def test_politeness_does_not_swallow_commands_questions_declines_or_clinical_text(text):
    assert acknowledgement(text) is None


def test_no_thanks_still_declines_pending_identity(client):
    pending=command(client,new(client),'Open Ayesha Khan report')
    result=command(client,pending['session'],'No thanks.','decline')
    assert result['session']['pending']['candidates']==[]
    assert result['kind']=='clarification'


@pytest.mark.parametrize('text',[
    "Thanks for this, also can you help me with the report's summary?",
    'Okay thanks, summarize her report.',
    'Thank you. Can you summarize her report?'
])
def test_mixed_thanks_and_summary_reaches_interpretation_with_full_request(client,monkeypatch,text):
    opened=command(client,new(client),'Open Priya Sharma report')
    original_plan=main.ai.plan;original_answer=main.ai.answer;seen=[]
    async def plan(message,context):
        seen.append(('plan',message));return await original_plan(message,context)
    async def answer(message,report,*args):
        seen.append(('answer',message));return await original_answer(message,report,*args)
    monkeypatch.setattr(main.ai,'plan',plan);monkeypatch.setattr(main.ai,'answer',answer)
    result=command(client,opened['session'],text,'mixed')
    assert seen==[('plan',text),('answer',text)]
    assert result['kind']=='answer' and result['evidence']
    assert all(e['report_id']==opened['report']['id'] for e in result['evidence'])
    assert result['session']==opened['session']
