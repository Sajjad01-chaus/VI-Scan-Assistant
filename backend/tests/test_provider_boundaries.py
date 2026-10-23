import asyncio
import copy
import json
import pytest
from backend.app.config import settings
from backend.app.providers import AI
from backend.app import providers
from backend.app.providers import ProviderError
from backend.app.schemas import GroundedAnswer
from backend.app.service import validate_findings
from fastapi import HTTPException

@pytest.mark.parametrize('text,action,name,expected_action,expected_name',[
    ('Summarize her report','summarize','Priya Sharma','summarize',''),
    ("Open Priya's latest report",'retrieve','Priya Sharma','retrieve','Priya'),
    ('Does this report confirm oral cancer?','retrieve','Priya Sharma','question',''),
    ("I asked what are the findings in Rohan Desai's report.",'retrieve','Rohan Desai','question','Rohan Desai'),
    ("Show me the findings in Rohan's report.",'retrieve','Rohan','question','Rohan'),
    ("Hey, open Rohan Desai's report.",'retrieve','Rohan Desai','retrieve','Rohan Desai')
])
def test_model_plan_cannot_expand_identity_from_context(monkeypatch,text,action,name,expected_action,expected_name):
    class Response:
        def json(self):return {'choices':[{'message':{'tool_calls':[{'function':{'name':'plan_assistant_action','arguments':json.dumps({'action':action,'patient_name':name,'modality':'ANY'})}}]}}]}
    async def fake(*args,**kwargs):return Response()
    monkeypatch.setattr(providers,'post',fake)
    cfg=copy.copy(settings);cfg.mode='live'
    plan=asyncio.run(AI(cfg).plan(text,{}))
    assert plan['action']==expected_action and plan['patient_name']==expected_name

def test_conflicting_sites_without_correction_require_clarification():
    text='Upper right second molar. Upper left second molar. No definite caries identified.'
    with pytest.raises(HTTPException,match='Conflicting anatomical sites'):
        validate_findings(text,[{'observation':'caries','anatomical_site':'upper left second molar','polarity':'negated','certainty':'not_definite','evidence':'No definite caries identified.'}])

def test_incomplete_observation_is_not_promoted_to_a_finding():
    with pytest.raises(HTTPException,match='Incomplete clinical observation'):
        validate_findings('Molar is',[{'observation':'Molar is','anatomical_site':'Molar','polarity':'unspecified','certainty':'asserted','evidence':'Molar is'}])

def test_invalid_structured_output_gets_one_repair(monkeypatch):
    cfg=copy.copy(settings);cfg.mode='live';calls=[]
    class Response:
        def __init__(self,text):self.text=text
        def json(self):return {'choices':[{'message':{'content':self.text}}]}
    async def fake(*args,**kwargs):
        calls.append(kwargs)
        return Response('not json' if len(calls)==1 else '{"claims":[]}')
    monkeypatch.setattr(providers,'post',fake)
    result=asyncio.run(AI(cfg).structured('Use only source evidence.','source',GroundedAnswer))
    assert result=={'claims':[]} and len(calls)==2

def test_schema_repair_does_not_loop_forever(monkeypatch):
    cfg=copy.copy(settings);cfg.mode='live';calls=[]
    class Response:
        def json(self):return {'choices':[{'message':{'content':'not json'}}]}
    async def fake(*args,**kwargs):calls.append(1);return Response()
    monkeypatch.setattr(providers,'post',fake)
    with pytest.raises(ProviderError,match='could not be validated'):
        asyncio.run(AI(cfg).structured('Use only source evidence.','source',GroundedAnswer))
    assert len(calls)==2

def test_anatomical_site_cannot_be_borrowed_from_an_unrelated_sentence():
    text='Possible caries in upper left first molar. No fracture in lower right third molar.'
    with pytest.raises(HTTPException,match='Unsupported anatomical association'):
        validate_findings(text,[{'observation':'caries','anatomical_site':'lower right third molar','polarity':'present','certainty':'uncertain','evidence':'Possible caries in upper left first molar.'}])

def test_positive_observation_cannot_gain_an_invented_negation():
    with pytest.raises(HTTPException,match='Unsupported negation'):
        validate_findings('Caries in upper left first molar.',[{'observation':'Caries','anatomical_site':'upper left first molar','polarity':'negated','certainty':'asserted','evidence':'Caries in upper left first molar.'}])

def test_immediate_anatomical_fragment_is_valid_context():
    result=validate_findings('Lower right third molar. Horizontally impacted.',[{'observation':'Horizontally impacted','anatomical_site':'Lower right third molar','polarity':'present','certainty':'asserted','evidence':'Horizontally impacted.'}])
    assert result[0]['anatomical_site']=='Lower right third molar'
