import pytest
from backend.app.drafts import render_draft_report
from backend.tests.test_workflows import client, new, command

def finding(observation='fracture', site='unspecified', polarity='negated', certainty='asserted', evidence='No evidence of fracture.'):
    return dict(observation=observation,anatomical_site=site,polarity=polarity,certainty=certainty,evidence=evidence)

def test_report_separates_positive_and_negative_findings():
    fields=[finding('horizontally impacted','lower right third molar','present','asserted','Lower right third molar is horizontally impacted.'),finding()]
    report=render_draft_report(fields,' '.join(f['evidence'] for f in fields))
    assert 'Findings\n- Lower right third molar: horizontally impacted.' in report
    assert 'Pertinent negatives\n- No evidence of fracture (site not specified).' in report
    assert 'Clinician review required; not a signed report.' in report

def test_uncertainty_and_explicit_recommendation_remain():
    text='Possible periapical radiolucency near the upper left first molar. Further assessment is required.'
    report=render_draft_report([finding('periapical radiolucency','upper left first molar','present','uncertain',text.split('.')[0]+'.')],text)
    assert 'Uncertain findings\n- Upper left first molar: possible periapical radiolucency.' in report
    assert 'Recorded recommendations\n- Further assessment is required.' in report
    assert 'infection' not in report.lower()

def test_no_definite_does_not_become_absent():
    report=render_draft_report([finding('caries','upper left second molar','negated','not_definite','No definite caries identified.')],'No definite caries identified.')
    assert 'no definite caries identified' in report
    assert 'No evidence of caries' not in report

def test_qualified_observation_retains_full_source_scope():
    fields=[finding('possible fracture',polarity='negated',certainty='uncertain',evidence='No evidence of a possible fracture.')]
    report=render_draft_report(fields,fields[0]['evidence'])
    assert 'No evidence of a possible fracture (site not specified).' in report

def test_uncertain_negative_retains_both_qualifiers():
    fields=[finding(certainty='uncertain',evidence='Possible fracture is not confirmed.')]
    report=render_draft_report(fields,fields[0]['evidence'])
    assert 'Possible fracture is not confirmed (site not specified).' in report

def test_correction_excludes_superseded_recommendation():
    text='Recommend extraction. Correction, further assessment is required.'
    report=render_draft_report([finding()],text)
    assert 'Recommend extraction' not in report
    assert 'further assessment is required' in report

def test_no_invented_recommendation_or_normality():
    report=render_draft_report([finding()],'No evidence of fracture.')
    assert 'Recorded recommendations' not in report
    assert 'normal' not in report.lower()
    assert 'Impression' not in report

@pytest.mark.parametrize('text',[
    'Lower right third molar is horizontally impacted. No evidence of a fracture.',
    'Possible periapical radiolucency near the upper left first molar. Further assessment is required.',
])
def test_report_survives_edit_save_read_and_history(client,text):
    opened=command(client,new(client),'Open Rohan Desai report')
    result=command(client,opened['session'],text,'draft','dictate')
    draft=result['draft'];fields=[{k:f[k] for k in ('observation','anatomical_site','polarity','certainty','evidence')} for f in draft['findings']]
    edited=client.patch('/api/drafts/'+draft['id'],json={'version':draft['version'],'findings':fields}).json()
    saved=client.post('/api/drafts/'+draft['id']+'/save',json={'version':edited['version']}).json()
    restored=client.get('/api/drafts/'+draft['id']).json()
    history=client.get('/api/sessions/'+opened['session']['id']+'/history').json()
    assert saved['status']=='saved_draft'
    assert all(d['readable_report']==draft['readable_report'] for d in (edited,saved,restored,history['drafts'][0]))
    assert restored['source_transcript']==text and restored['findings']==draft['findings']

def test_invalid_certainty_never_updates_report(client):
    text='Possible periapical radiolucency near the upper left first molar. Further assessment is required.'
    opened=command(client,new(client),'Open Rohan Desai report')
    draft=command(client,opened['session'],text,'draft','dictate')['draft']
    fields=[{k:f[k] for k in ('observation','anatomical_site','polarity','certainty','evidence')} for f in draft['findings']]
    fields[0]['certainty']='asserted'
    response=client.patch('/api/drafts/'+draft['id'],json={'version':draft['version'],'findings':fields})
    assert response.status_code==422
    restored=client.get('/api/drafts/'+draft['id']).json()
    assert restored['version']==draft['version'] and restored['readable_report']==draft['readable_report']
