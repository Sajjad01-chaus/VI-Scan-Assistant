import pytest
from backend.tests.test_workflows import client,new,command
import backend.app.main as main


@pytest.mark.parametrize('reply',[
    "Actually it's Priya Sharma.", 'Actually it is Priya Sharma.',
    "Sorry, it's Priya Sharma.", 'Well, actually, I meant Priya Sharma.',
    'Okay, the patient is Priya Sharma.', 'Actually Priya Sharma please.',
    "Yes, actually it's Priya Sharma."
])
def test_conversational_framing_preserves_pending_request(client,reply):
    pending=command(client,new(client),"Open Priya's latest OPG report")
    result=command(client,pending['session'],reply,'correction')
    assert result['report']['id']=='RPT-001-03' and result['session']['pending'] is None


@pytest.mark.parametrize('proposed,decision,allowed',[
    ('Priya Sharma','choose',True),
    ('Priya Shah','choose',False),
    ('PT-001','choose',False),
    ('Priya Sharma','unresolved',False)
])
def test_semantic_reply_interpretation_cannot_invent_identity(client,monkeypatch,proposed,decision,allowed):
    pending=command(client,new(client),"Open Priya's latest CBCT report")
    seen=[]
    async def interpret(text,candidates):
        seen.append((text,candidates));return {'decision':decision,'patient_name':proposed}
    monkeypatch.setattr(main.ai,'interpret_identity_reply',interpret)
    result=command(client,pending['session'],'The person I was referring to was Priya Sharma.','correction')
    assert len(seen)==1
    if allowed:assert result['report']['id']=='RPT-001-02'
    else:assert result['session']['pending']==pending['session']['pending'] and not result['evidence']


@pytest.mark.parametrize('reply',[
    'Actually not Priya Sharma.', 'Does Priya Sharma have cancer?',
    'What are the findings for Priya Sharma?', 'Open Priya Sharma report'
])
def test_negative_and_question_replies_are_not_semantic_identity_selections(client,monkeypatch,reply):
    pending=command(client,new(client),"Open Priya's latest OPG report")
    async def forbidden(*args):raise AssertionError('Must not infer confirmation for this reply')
    monkeypatch.setattr(main.ai,'interpret_identity_reply',forbidden)
    result=command(client,pending['session'],reply,'correction')
    if not reply.startswith('Open'):assert result['session']['pending'] and not result['evidence']
