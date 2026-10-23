import asyncio
import copy
import json
import pytest
from fastapi import HTTPException
from backend.app.answers import compose_answer
from backend.app.config import settings
from backend.app.providers import AI

REPORT={'id':'RPT-TEST','version':2,'content':'Possible periapical radiolucency near the upper left first molar. Further clinical assessment is required. A restoration is described at the upper left first molar.'}

def claim(quote,purpose='finding',text=None):
    return {'text':text or quote,'evidence':quote,'purpose':purpose}

def test_combined_summary_and_cause_is_concise_uncertain_and_explicitly_abstains():
    first='Possible periapical radiolucency near the upper left first molar.'
    follow='Further clinical assessment is required.'
    result=compose_answer('Can you summarize it? What is her main cause?',REPORT,[claim(first),claim(first),claim(follow,'next_step')],True)
    assert 'possible darker area' in result['message']
    assert 'underlying cause' in result['message'] and result['cause_not_established']
    assert follow in result['message'] and len(result['evidence'])==2
    assert result['evidence'][0]['quote']==first
    assert len(result['message'].split())<70

def test_unchecked_model_prose_is_never_spoken():
    result=compose_answer('Summarize it',REPORT,[claim(REPORT['content'].split('. ')[0]+'.',text='She definitely has an infection caused by poor hygiene.')],True)
    assert 'infection' not in result['message'] and 'poor hygiene' not in result['message']
    assert 'possible' in result['message']

def test_valid_quote_with_false_cause_label_does_not_invent_a_cause():
    result=compose_answer('What caused it?',REPORT,[claim('A restoration is described at the upper left first molar.','cause')])
    assert result['cause_not_established'] and not result['evidence']
    assert 'restoration' not in result['message']

def test_explicit_source_cause_is_quoted_not_inferred():
    report={'id':'TEST','version':1,'content':'The stated cause is a documented mock event.'}
    result=compose_answer('What is the cause?',report,[claim(report['content'],'cause')])
    assert report['content'] in result['message'] and not result['cause_not_established']
    assert result['evidence'][0]['quote']==report['content']

def test_invalid_quote_is_rejected():
    with pytest.raises(HTTPException,match='unsupported source evidence'):
        compose_answer('Summarize',REPORT,[claim('Cancer is present.')],True)

def test_unanswered_question_still_abstains_without_citations():
    result=compose_answer('Does it confirm cancer?',REPORT,[])
    assert not result['evidence'] and 'not stated' in result['message']

def test_summary_request_preserves_the_original_compound_question(monkeypatch):
    config=copy.copy(settings);config.mode='live';ai=AI(config);seen={}
    async def capture(prompt,text,schema):
        seen.update(json.loads(text));return {'claims':[]}
    monkeypatch.setattr(ai,'structured',capture)
    question='Can you summarize it like what happened to her? What is her main cause?'
    asyncio.run(ai.answer(question,REPORT,True,[]))
    assert seen['request']==question and seen['summary_requested'] is True

def test_negated_causal_sentence_does_not_establish_a_cause():
    report={'id':'TEST','version':1,'content':'It was not caused by the recorded mock event.'}
    result=compose_answer('What caused it?',report,[claim(report['content'],'cause')])
    assert result['cause_not_established'] and not result['evidence']

def test_diagnosis_question_rejects_valid_but_unrelated_evidence():
    result=compose_answer('Does her report confirm oral cancer?',REPORT,[claim('Possible periapical radiolucency near the upper left first molar.')])
    assert not result['evidence'] and 'cannot infer' in result['message']
    assert 'darker area' not in result['message']

def test_explicit_negative_diagnosis_evidence_is_preserved():
    report={'id':'TEST','version':1,'content':'No fracture is identified. A restoration is present.'}
    result=compose_answer('Does it confirm a fracture?',report,[claim('A restoration is present.'),claim('No fracture is identified.','limitation')])
    assert result['message']=='No fracture is identified.'
    assert len(result['evidence'])==1

def test_summary_and_unsupported_diagnosis_address_both_parts():
    result=compose_answer('Summarize and does her report confirm cancer?',REPORT,[claim('Possible periapical radiolucency near the upper left first molar.')],True)
    assert 'possible darker area' in result['message'] and 'does not establish that diagnosis' in result['message']

def test_technical_limitation_is_explained_but_original_evidence_is_retained():
    report={'id':'TEST','version':1,'content':'Superimposition limits assessment of the apices.'}
    result=compose_answer('What is the limitation?',report,[claim(report['content'],'limitation')])
    assert result['message']=='Overlapping structures make the root tips difficult to assess.'
    assert result['evidence'][0]['quote']==report['content']


@pytest.mark.parametrize('source,expected',[
    ('Lower right third molar is horizontally impacted.','lower right wisdom tooth is lying sideways'),
    ('Horizontally impacted lower right third molar.','lower right wisdom tooth is lying sideways'),
    ('Lower left third molar is partially erupted.','lower left wisdom tooth has only partly come through'),
    ('Synthetic panoramic dental radiograph text scenario.','mock report describes a panoramic dental X-ray (OPG)'),
    ('The relationship to the inferior alveolar canal cannot be determined confidently on this panoramic examination.','cannot clearly establish how the tooth relates to the nerve canal'),
    ('No definite carious lesion is established in the described tooth; early disease is not excluded.','early decay cannot be ruled out'),
])
def test_reviewed_plain_language_preserves_the_original_citation(source,expected):
    report={'id':'TEST','version':2,'content':source}
    result=compose_answer('Explain the report in simple words',report,[claim(source)])
    assert expected in result['message']
    assert result['evidence']==[{'report_id':'TEST','report_version':2,'quote':source,'start':0,'end':len(source)}]


def test_cause_abstention_explains_known_finding_and_recommendation_without_inference():
    finding='Possible periapical radiolucency near the upper left first molar.'
    step='Further clinical assessment is required.'
    result=compose_answer('Does the report establish the exact cause?',REPORT,[claim(finding),claim(step,'next_step')])
    assert 'possible darker area' in result['message'] and 'does not establish the underlying cause' in result['message']
    assert step in result['message'] and len(result['evidence'])==2 and result['cause_not_established']
    assert 'infection' not in result['message']


def test_unknown_sentence_is_not_paraphrased_into_new_clinical_claims():
    source='The tooth may be partially erupted.'
    result=compose_answer('Explain it',{'id':'TEST','version':1,'content':source},[claim(source)])
    assert result['message']==source

@pytest.mark.parametrize('question',[
    'Have you find any key findings in her report?',
    'Have you found any key findings in her report?',
    'Did you find anything important?',
    'What are the key findings?',
    'Any findings?',
    'Has the report mentioned a finding?',
    'Have you summarized her report?'
])
def test_general_observation_questions_are_not_diagnosis_targets(question):
    from backend.app.answers import diagnosis_terms
    assert diagnosis_terms(question)==set()
    report={'id':'RPT-006-03','version':2,'content':'No definite periapical radiolucency is identified in the described region. Clinical correlation is advised.'}
    result=compose_answer(question,report,[claim('No definite periapical radiolucency is identified in the described region.')])
    assert result['evidence'] and 'No definite' in result['message']
    assert 'not stated' not in result['message']

@pytest.mark.parametrize('question',['Does she have cancer?','Does her report confirm oral cancer?','Has she been diagnosed with cancer?','Is it cancer?'])
def test_explicit_condition_questions_still_abstain_when_condition_is_absent(question):
    result=compose_answer(question,REPORT,[claim('Possible periapical radiolucency near the upper left first molar.')])
    assert not result['evidence'] and 'cannot infer' in result['message']

@pytest.mark.parametrize('question',['Does she have any findings?','Does she have key observations in her report?','Does she have any abnormalities?'])
def test_generic_patient_observation_objects_are_not_named_diagnoses(question):
    from backend.app.answers import diagnosis_terms
    assert diagnosis_terms(question)==set()

def test_findings_of_named_diagnosis_does_not_bypass_topic_check():
    result=compose_answer('Does she have findings of cancer?',REPORT,[claim('Possible periapical radiolucency near the upper left first molar.')])
    assert not result['evidence'] and 'cannot infer' in result['message']
