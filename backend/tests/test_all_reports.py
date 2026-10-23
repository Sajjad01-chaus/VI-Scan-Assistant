import pytest
from backend.tests.test_workflows import client, new, command
from backend.app import db as store
from backend.app.providers import ProviderError
import backend.app.main as main


@pytest.mark.parametrize('summary_request',[
    'Summarize her all reports.', 'Summarize all her reports.',
    'Give a summary of every report.', 'Summarize her complete report history.'
])
def test_all_reports_summary_preserves_selected_report_and_sources(client,summary_request):
    opened=command(client,new(client),"Open Priya Sharma's latest CBCT report")
    result=command(client,opened['session'],summary_request,'all')
    expected=['RPT-001-03','RPT-001-02','RPT-001-01']
    assert result['complete'] and result['report_ids']==expected
    assert {e['report_id'] for e in result['evidence']}==set(expected)
    assert result['session']==opened['session']
    assert result['trace'][0]['tool']=='list_patient_reports'
    with main.service.factory() as db:
        for e in result['evidence']:
            report=db.get(store.Report,e['report_id'])
            assert report.patient_id=='PT-001' and report.version==e['report_version']
            assert report.content[e['start']:e['end']]==e['quote']
            assert report.performed_at in result['message']
    restored=client.get('/api/sessions/'+opened['session']['id']+'/history').json()
    assert restored['messages'][-1]['result']['report_ids']==expected
    assert len(result['speech_text'])<600 and 'shown in the conversation' in result['speech_text']


def test_all_reports_modality_filter_and_patient_switch(client):
    opened=command(client,new(client),"Open Priya Sharma's latest CBCT report")
    result=command(client,opened['session'],'Summarize all her OPG reports','opg')
    assert result['report_ids']==['RPT-001-03','RPT-001-01']
    switched=command(client,result['session'],"Open Meera Iyer's report",'switch')
    current=command(client,switched['session'],'Summarize all her reports','meera')
    assert {e['report_id'] for e in current['evidence']}=={'RPT-006-01','RPT-006-02','RPT-006-03'}


def test_unresolved_identity_never_lists_all_reports(client,monkeypatch):
    pending=command(client,new(client),"Open Priya's report")
    async def forbidden(*args,**kwargs):raise AssertionError('Must not summarize unresolved patient')
    monkeypatch.setattr(main.ai,'answer',forbidden)
    result=command(client,pending['session'],'Summarize all her reports','all')
    assert result['kind']=='clarification' and not result['evidence'] and not result['trace']


@pytest.mark.parametrize('failure',['outage','fabricated','empty'])
def test_partial_failure_is_explicit_without_invented_evidence(client,monkeypatch,failure):
    opened=command(client,new(client),"Open Priya Sharma's report")
    answer=main.ai.answer
    async def fail_one(text,report,*args):
        if report['id']=='RPT-001-02':
            if failure=='outage':raise ProviderError()
            return {'claims':[] if failure=='empty' else [{'text':'invented','evidence':'Invented diagnosis.','purpose':'finding'}]}
        return await answer(text,report,*args)
    monkeypatch.setattr(main.ai,'answer',fail_one)
    result=command(client,opened['session'],'Summarize all her reports','all')
    assert not result['complete'] and result['failed_report_ids']==['RPT-001-02']
    assert 'Incomplete summary: 1 of 3' in result['message']
    assert {e['report_id'] for e in result['evidence']}=={'RPT-001-03','RPT-001-01'}
    assert result['trace'][2]['status']=='failed'


def test_missing_modality_does_not_prevent_all_reports_summary(client):
    missing=command(client,new(client),"Open Meera Iyer's OPG report")
    result=command(client,missing['session'],'Summarize all her reports','all')
    assert result['complete'] and len(result['report_ids'])==3
    filtered=command(client,result['session'],'Summarize all her OPG reports','opg')
    assert filtered['kind']=='missing_report' and not filtered['evidence']


def test_selected_report_summary_does_not_expand_scope(client):
    opened=command(client,new(client),"Open Priya Sharma's CBCT report")
    result=command(client,opened['session'],'Summarize her report','one')
    assert {e['report_id'] for e in result['evidence']}=={'RPT-001-02'}
    assert 'report_ids' not in result


def test_all_reports_requires_selected_patient(client):
    result=command(client,new(client),'Summarize all her reports')
    assert result['kind']=='clarification' and not result['evidence']


def test_spoken_overview_uses_persisted_text_without_cloud(client,monkeypatch):
    opened=command(client,new(client),"Open Priya Sharma's report")
    result=command(client,opened['session'],'Summarize all her reports','all')
    captured=[]
    async def speak(text):captured.append(text);return b'local-test-audio','audio/wav','test'
    monkeypatch.setattr(main.ai,'speak',speak)
    response=client.post('/api/sessions/'+opened['session']['id']+'/speech',json={'turn_id':result['turn_id']})
    assert response.status_code==200 and captured==[result['speech_text']]
