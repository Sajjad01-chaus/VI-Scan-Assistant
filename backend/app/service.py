import asyncio
import hashlib
import json
import re
import time
import uuid
from difflib import SequenceMatcher
from sqlalchemy import select
from fastapi import HTTPException
from . import db as store
from .schemas import Finding, Extraction
from .providers import ProviderError, normalize_plan
from .answers import compose_answer, all_reports_requested

def uid():return str(uuid.uuid4())
def digest(token):return hashlib.sha256(token.encode()).hexdigest()
def patient_dict(p):return {'id':p.id,'name':p.name,'reference':p.reference}
def report_dict(r):return {'id':r.id,'patient_id':r.patient_id,'modality':r.modality,'performed_at':r.performed_at,'version':r.version,'content':r.content,'synthetic':True}

def acknowledgement(text):
    normalized=' '.join(re.findall(r'[a-z0-9]+',text.casefold().replace('’',"'").replace("'",'')))
    phrase=r'(?:okay|ok|alright|all right|got it|understood|great|perfect|sounds good|thats all|thanks(?: a lot| so much)?|thank you(?: very much| so much| for (?:your |the )?help)?)'
    if re.fullmatch(r'(?:'+phrase+r')(?:\s+'+phrase+r')*',normalized):
        return 'You’re welcome.' if re.search(r'\b(thank|thanks)\b',normalized) else 'Okay.'
    return None

def identity_reply_text(text):
    normalized=' '.join(re.findall(r'[a-z0-9]+',text.casefold().replace('’',"'").replace("'",'')))
    normalized=re.sub(r'^(?:(?:actually|sorry|well|okay|ok|yes|please)\s+)+','',normalized)
    identity=re.sub(r'^(?:yes |no )?(?:its |it is |i mean |i meant |the patient is |patient is |the name is |choose |select |go with |use )','',normalized)
    return re.sub(r' please$','',identity)

def pending_patient_reply(text, pending, allow_short_names=True):
    """Resolve explicit identity replies; never infer an unspoken patient."""
    identity=identity_reply_text(text)
    candidates=pending['candidates']
    ordinal=re.fullmatch(r'(?:the )?(first|second|third)(?: one| patient)?',identity)
    if ordinal and allow_short_names:
        index={'first':0,'second':1,'third':2}[ordinal[1]]
        return candidates[index]['id'] if index<len(candidates) else None
    matches=[]
    for patient in candidates:
        name=patient['name'].casefold()
        identifiers={name,patient['id'].casefold().replace('-',' '),patient['reference'].casefold().replace('-',' ')}
        if allow_short_names:identifiers.add(name.split()[-1])
        if identity in identifiers:matches.append(patient['id'])
    return matches[0] if len(matches)==1 else None

def validate_findings(transcript, findings):
    """Conservative deterministic provenance checks, not a semantic entailment oracle."""
    checked=[]
    for item in findings:
        f=Finding.model_validate(item).model_dump()
        if f['evidence'] not in transcript or f['observation'].lower() not in f['evidence'].lower():
            raise HTTPException(422,'Unsupported clinical claim: observation must be quoted within its source evidence.')
        if f['anatomical_site']!='unspecified' and f['anatomical_site'].lower() not in transcript.lower():
            raise HTTPException(422,'Unsupported anatomical site. Keep unspecified details unspecified.')
        e=f['evidence'].lower()
        if re.search(r'\b(is|are|was|were|has|have|of|the|near|with|and)[.!?\s]*$',e):
            raise HTTPException(422,'Incomplete clinical observation. Finish the phrase before creating a draft.')
        negated=bool(re.search(r'\b(no|not|without|absent)\b',e))
        if negated and f['polarity']!='negated':raise HTTPException(422,'Negation must be preserved.')
        if not negated and f['polarity']=='negated':raise HTTPException(422,'Unsupported negation: the source evidence does not negate this observation.')
        if re.search(r'\b(possible|possibly|suspected|may|might|uncertain)\b',e) and f['certainty']!='uncertain':
            raise HTTPException(422,'Uncertainty must be preserved.')
        if 'no definite' in e and f['certainty']!='not_definite':raise HTTPException(422,'The qualifier "no definite" must be preserved.')
        if 'correction' not in transcript.lower() and 'upper right' in transcript.lower() and 'upper left' in transcript.lower():
            raise HTTPException(422,'Conflicting anatomical sites: clarify the intended site before creating this draft.')
        if f['anatomical_site']!='unspecified' and f['anatomical_site'].casefold() not in e:
            prefix=transcript[:transcript.index(f['evidence'])].rstrip(' .!?\n\t')
            preceding=re.split(r'[.!?\n]',prefix)[-1].strip()
            preceding=re.sub(r'^correction[,\s:]*','',preceding,flags=re.I)
            normalize=lambda value:' '.join(re.findall(r'[a-z0-9]+',value.casefold()))
            if normalize(preceding)!=normalize(f['anatomical_site']):
                raise HTTPException(422,'Unsupported anatomical association: quote the site with this finding or use an immediately preceding anatomical fragment.')
        f['source_span']={'start':transcript.index(f['evidence']),'end':transcript.index(f['evidence'])+len(f['evidence'])}
        f['review_flags']=['Clinician review required']
        checked.append(f)
    if not checked:raise HTTPException(422,'No supported clinical observations were found.')
    return checked

class Service:
    def __init__(self, ai, factory=None):
        self.ai=ai
        self.factory=factory or store.Session
        self.locks={}

    def owned(self, session_id, owner):
        with self.factory() as db:
            s=db.get(store.Conversation,session_id)
            if not s or not owner or s.owner_hash!=digest(owner):raise HTTPException(404,'Session not found.')
            if s.expires_at<time.time():raise HTTPException(410,'Session expired. Create a new session.')
            return s

    def snapshot(self, session_id, owner):
        s=self.owned(session_id,owner)
        with self.factory() as db:
            patient=db.get(store.Patient,s.selected_patient_id) if s.selected_patient_id else None
            report=db.get(store.Report,s.selected_report_id) if s.selected_report_id else None
            pending=json.loads(s.pending_json) if s.pending_json else None
            return {'id':s.id,'context_version':s.context_version,'patient':patient_dict(patient) if patient else None,'report':report_dict(report) if report else None,'pending':pending,'expires_at':s.expires_at,'mode':self.ai.config.mode}

    def new_session(self, owner):
        s=store.Conversation(id=uid(),owner_hash=digest(owner),context_version=0,expires_at=time.time()+86400)
        with self.factory.begin() as db:db.add(s)
        return self.snapshot(s.id,owner)

    def history(self, session_id, owner):
        self.owned(session_id,owner)
        with self.factory() as db:
            turns=db.scalars(select(store.Turn).where(store.Turn.session_id==session_id).order_by(store.Turn.created_at,store.Turn.id)).all()
            messages=[]
            for turn in turns:
                request=json.loads(turn.request_json or '{}')
                if request.get('text'):messages.append({'role':'user','text':request['text']})
                if turn.response_json:
                    result=json.loads(turn.response_json)
                    messages.append({'role':'assistant','text':result['message'],'result':result})
            drafts=db.scalars(select(store.Draft).where(store.Draft.session_id==session_id)).all()
            return {'messages':messages,'drafts':[{'id':d.id,'patient_id':d.patient_id,'version':d.version,'status':d.status,**json.loads(d.body_json)} for d in drafts]}

    def recent_dialogue(self, session_id, snap):
        with self.factory() as db:
            turns=db.scalars(select(store.Turn).where(store.Turn.session_id==session_id,store.Turn.response_json.is_not(None)).order_by(store.Turn.created_at.desc(),store.Turn.id.desc()).limit(6)).all()
        dialogue=[]
        for turn in reversed(turns):
            response=json.loads(turn.response_json)
            previous=response.get('session',{})
            if (previous.get('patient') or {}).get('id')!=(snap.get('patient') or {}).get('id'):continue
            if (previous.get('report') or {}).get('id')!=(snap.get('report') or {}).get('id'):continue
            if (previous.get('report') or {}).get('version')!=(snap.get('report') or {}).get('version'):continue
            request=json.loads(turn.request_json or '{}')
            if request.get('text'):dialogue.append({'role':'user','text':request['text'][:1000]})
            dialogue.append({'role':'assistant','text':response['message'][:1000]})
        return dialogue

    def search(self, query):
        q=re.sub(r'[^a-z0-9 ]','',query.casefold()).strip()
        if not q:return []
        with self.factory() as db:
            patients=db.scalars(select(store.Patient).order_by(store.Patient.name)).all()
            exact=[p for p in patients if p.name.casefold()==q or re.sub(r'[^a-z0-9]','',p.id.casefold())==q.replace(' ','')]
            matches=exact or [p for p in patients if all(t in p.name.casefold().split() for t in q.split())]
            return [patient_dict(p) for p in matches]

    def audit(self, session_id, event, metadata=None):
        with self.factory.begin() as db:db.add(store.AuditEvent(id=uid(),session_id=session_id,event_type=event,metadata_json=json.dumps(metadata or {})))

    def suggest_patients(self, name):
        """Recovery candidates only: approximate names never select a patient."""
        tokens=re.findall(r'[a-z]+',name.casefold())
        if len(tokens)<2:return []
        with self.factory() as db:
            patients=db.scalars(select(store.Patient).order_by(store.Patient.name)).all()
            matches=[]
            for patient in patients:
                parts=patient.name.casefold().split()
                same_family=parts[-1]==tokens[-1] and SequenceMatcher(None,' '.join(tokens[:-1]),' '.join(parts[:-1])).ratio()>=.55
                first_key=re.sub(r'[aeiouy]','',tokens[0])
                patient_key=re.sub(r'[aeiouy]','',parts[0])
                similar_first=tokens[0]==parts[0] or (len(first_key)>=2 and first_key==patient_key and SequenceMatcher(None,tokens[0],parts[0]).ratio()>=.6)
                if same_family or similar_first:matches.append(patient_dict(patient))
            return matches

    def question_identity_matches(self, text, proposed_name):
        text=re.sub(r"['’]s\b",'',text.casefold())
        with self.factory() as db:
            directory=db.scalars(select(store.Patient).order_by(store.Patient.name)).all()
            full=[p for p in directory if re.search(r'\b'+re.escape(p.name.casefold())+r'\b',text)]
            remaining=text
            for patient in full:remaining=re.sub(r'\b'+re.escape(patient.name.casefold())+r'\b','',remaining)
            first=[p for p in directory if re.search(r'\b'+re.escape(p.name.casefold().split()[0])+r'\b',remaining)]
            mentioned=list({p.id:p for p in full+first}.values())
            if mentioned:return [patient_dict(p) for p in mentioned]
        return self.search(proposed_name) if proposed_name else None

    def retrieve(self, session_id, owner, name, modality, trace):
        snap=self.snapshot(session_id,owner)
        trace.append({'tool':'search_patients','arguments':{'query':name}})
        candidates=self.search(name)
        if not candidates:
            suggestions=self.suggest_patients(name)
            with self.factory.begin() as db:
                s=db.get(store.Conversation,session_id)
                s.pending_json=json.dumps({'candidates':suggestions,'modality':modality,'query':name,'approximate':True})
                s.context_version+=1
            if suggestions:
                message=(f'Did you mean {suggestions[0]["name"]}, patient {suggestions[0]["id"]}? Say yes or no, or choose below.' if len(suggestions)==1 else f'I heard "{name}". Which patient did you mean? Please choose a patient below.')
                return {'kind':'candidates','message':message,'candidates':suggestions,'evidence':[]}
            return {'kind':'clarification','message':f'I could not match "{name}". Say just the corrected full name or patient ID, or select a patient from the directory. I will keep your report request.','evidence':[]}
        if len(candidates)>1:
            with self.factory.begin() as db:
                s=db.get(store.Conversation,session_id)
                s.pending_json=json.dumps({'candidates':candidates,'modality':modality})
                s.context_version+=1
            return {'kind':'candidates','message':'More than one patient matches. Select the intended patient before continuing.','candidates':candidates,'evidence':[]}
        return self.choose_report(session_id,owner,candidates[0]['id'],modality,trace)

    def choose_report(self, session_id, owner, patient_id, modality, trace):
        self.owned(session_id,owner)
        trace.append({'tool':'get_latest_report','arguments':{'patient_id':patient_id,'modality':modality}})
        with self.factory.begin() as db:
            s=db.get(store.Conversation,session_id)
            p=db.get(store.Patient,patient_id)
            if not p:raise HTTPException(404,'Patient not found.')
            query=select(store.Report).where(store.Report.patient_id==patient_id)
            if modality!='ANY':query=query.where(store.Report.modality==modality)
            r=db.scalar(query.order_by(store.Report.performed_at.desc(),store.Report.id.desc()))
            s.selected_patient_id=patient_id;s.selected_report_id=r.id if r else None
            s.pending_json=None;s.context_version+=1
            if not r:return {'kind':'missing_report','message':f'No {modality} report is available for {p.name}. The active report has been cleared.','evidence':[]}
            result={'kind':'report','message':f'Opened {p.name}’s latest {r.modality} report.','report':report_dict(r),'evidence':[{'report_id':r.id,'report_version':r.version,'quote':r.content,'start':0,'end':len(r.content)}]}
        self.audit(session_id,'report.selected',{'report_id':r.id})
        return result

    async def select_patient(self, session_id, owner, selection):
        async with self.locks.setdefault(session_id,asyncio.Lock()):
            snap=self.snapshot(session_id,owner)
            if selection.context_version!=snap['context_version']:raise HTTPException(409,'Context changed. Refresh before selecting.')
            pending=snap['pending']
            if not pending or selection.patient_id not in {p['id'] for p in pending['candidates']}:raise HTTPException(422,'Selection is not one of the pending patient candidates.')
            trace=[]
            result=self.choose_report(session_id,owner,selection.patient_id,pending['modality'],trace)
            turn_id=uid()
            result=self.envelope(session_id,owner,result,trace,turn_id)
            with self.factory.begin() as db:
                db.add(store.Turn(id=turn_id,session_id=session_id,utterance_id='selection-'+turn_id,request_json=json.dumps({'text':'Selected patient '+selection.patient_id}),response_json=json.dumps(result)))
            return result

    def envelope(self, session_id, owner, result, trace, turn_id=None, elapsed=None):
        return {**result,'turn_id':turn_id,'session':self.snapshot(session_id,owner),'trace':trace,'mode':self.ai.config.mode,'elapsed_ms':elapsed}

    async def summarize_patient_reports(self, session_id, snap, request, trace):
        patient=snap['patient']
        modality=next((m for m in ['OPG','CBCT','IOPA'] if re.search(r'\b'+m+r'\b',request,re.I)),'ANY')
        trace.append({'tool':'list_patient_reports','arguments':{'patient_id':patient['id'],'modality':modality}})
        with self.factory() as db:
            query=select(store.Report).where(store.Report.patient_id==patient['id'])
            if modality!='ANY':query=query.where(store.Report.modality==modality)
            reports=[report_dict(r) for r in db.scalars(query.order_by(store.Report.performed_at.desc(),store.Report.id.desc())).all()]
        if not reports:return {'kind':'missing_report','message':f'No {modality} reports are available for {patient["name"]}.','evidence':[]}
        semaphore=asyncio.Semaphore(3)
        async def summarize(report):
            async with semaphore:
                try:
                    raw=await self.ai.answer(request,report,True,[])
                    answer=compose_answer(request,report,raw['claims'],True)
                    if not answer['evidence']:return {'report':report,'error':'No supported summary could be extracted.'}
                    return {'report':report,'answer':answer}
                except (ProviderError,HTTPException):
                    return {'report':report,'error':'Summary unavailable because generation or source validation failed.'}
        results=await asyncio.gather(*(summarize(r) for r in reports))
        evidence=[];sections=[];failures=[]
        for item in results:
            report=item['report']
            trace.append({'tool':'summarize_report','arguments':{'report_id':report['id']},'status':'failed' if 'error' in item else 'completed'})
            header=f'{report["modality"]} · {report["performed_at"]} · {report["id"]}'
            sections.append(header+'\n'+(item.get('error') or item['answer']['message']))
            if 'error' in item:failures.append(report['id'])
            else:evidence.extend(item['answer']['evidence'])
        scope='all available reports' if modality=='ANY' else f'all available {modality} reports'
        status=f'Incomplete summary: {len(failures)} of {len(reports)} reports could not be summarized.' if failures else f'Summary of {scope} ({len(reports)}) for {patient["name"]}.'
        self.audit(session_id,'reports.summarized',{'patient_id':patient['id'],'report_ids':[r['id'] for r in reports],'failed_report_ids':failures})
        speech_text=status+' The report-by-report findings, dates, limitations and source citations are shown in the conversation.'
        return {'kind':'answer','message':status+'\n\n'+'\n\n'.join(sections),'speech_text':speech_text,'evidence':evidence,'report_scope':'all_patient_reports','report_ids':[r['id'] for r in reports],'failed_report_ids':failures,'complete':not failures}

    async def command(self, session_id, owner, command):
        start=time.perf_counter()
        self.owned(session_id,owner)
        async with self.locks.setdefault(session_id,asyncio.Lock()):
            with self.factory() as db:
                old=db.scalar(select(store.Turn).where(store.Turn.session_id==session_id,store.Turn.utterance_id==command.utterance_id))
                if old:
                    if old.response_json:return {**json.loads(old.response_json),'session':self.snapshot(session_id,owner),'replayed':True}
                    raise HTTPException(409,'This utterance is already processing or was interrupted. Use a new utterance ID to retry.')
            snap=self.snapshot(session_id,owner)
            if command.context_version!=snap['context_version']:raise HTTPException(409,'Patient context changed. Refresh before retrying.')
            turn_id=uid()
            with self.factory.begin() as db:db.add(store.Turn(id=turn_id,session_id=session_id,utterance_id=command.utterance_id,request_json=command.model_dump_json()))
            trace=[]
            try:
                pending_id=pending_patient_reply(command.text,snap['pending']) if command.intent=='auto' and snap['pending'] else None
                confirmation=re.sub(r'[^a-z ]','',command.text.casefold()).strip()
                confirmation=' '.join(confirmation.split())
                reply=identity_reply_text(command.text)
                polite_reply=acknowledgement(command.text) if command.intent=='auto' else None
                recovery_scope=False
                if command.intent=='auto' and snap['pending'] and not snap['pending']['candidates']:
                    with self.factory() as db:
                        directory=[patient_dict(p) for p in db.scalars(select(store.Patient).order_by(store.Patient.name)).all()]
                    pending_id=pending_patient_reply(command.text,{'candidates':directory},allow_short_names=False)
                    recovery_scope=bool(pending_id)
                if command.intent=='auto' and snap['pending'] and not pending_id and not polite_reply and not re.search(r'\b(no|not|never|does|is|what|why|how|can|findings|observations|pain|open|find|show|retrieve|locate|summarize)\b',command.text,re.I) and not command.text.rstrip().endswith('?'):
                    scope=snap['pending']['candidates']
                    if scope and any(re.search(r'\b'+re.escape(token)+r'\b',command.text,re.I) for p in scope for token in p['name'].split()):
                        interpreted=await self.ai.interpret_identity_reply(command.text,scope)
                        name=interpreted['patient_name'].strip()
                        if interpreted['decision']=='choose' and name and re.search(r'\b'+re.escape(name)+r'\b',command.text,re.I):
                            pending_id=pending_patient_reply(name,snap['pending'])
                if polite_reply:
                    message=polite_reply
                    if snap['pending']:message+=' I still have your report request. Say the patient’s full name when you’re ready.'
                    plan={'action':'acknowledge','message':message}
                elif pending_id:
                    plan={'action':'select_pending','patient_id':pending_id}
                elif command.intent=='auto' and snap['pending'] and not snap['pending']['candidates'] and not re.search(r'\b(no|not|does|is|what|why|how|can|report|summarize|open|find|show|retrieve|locate)\b',reply) and self.suggest_patients(reply):
                    plan={'action':'retrieve','patient_name':reply,'modality':snap['pending']['modality']}
                elif command.intent=='auto' and snap['pending'] and confirmation in {'yes','yes please','yes thats correct','thats correct','correct','yes open it','no','no thanks','no thats wrong','thats wrong'}:
                    plan={'action':'decline' if confirmation in {'no','no thanks','no thats wrong','thats wrong'} else 'confirm','patient_name':'','modality':'ANY'}
                elif command.intent=='dictate':plan={'action':'dictate','patient_name':'','modality':'ANY'}
                elif snap['pending'] and not re.search(r'\b(open|find|show|retrieve|locate)\b',command.text,re.I):
                    followup=bool(re.search(r'\b(summari[sz]e|summary)\b',command.text,re.I) or command.text.rstrip().endswith('?') or re.match(r'^(does|is|are|what|why|how|can)\b',command.text,re.I))
                    plan={'action':'question' if followup else 'clarify','patient_name':''}
                else:plan=await self.ai.plan(command.text,{'selected_patient':snap['patient'],'selected_report_id':snap['report']['id'] if snap['report'] else None,'pending_identity':bool(snap['pending']),'pending_choices':snap['pending']['candidates'] if snap['pending'] else [],'recent_dialogue':self.recent_dialogue(session_id,snap)})
                if plan['action'] in {'retrieve','question','summarize','summarize_all'}:plan=normalize_plan(command.text,plan)
                action=plan['action']
                if action=='acknowledge':
                    result={'kind':'acknowledgement','message':plan['message'],'evidence':[]}
                elif action=='select_pending':
                    trace.append({'tool':'resolve_pending_patient','arguments':{'patient_id':pending_id,'source':'corrected full directory identity' if recovery_scope else 'current reply and pending session choices'}})
                    result=self.choose_report(session_id,owner,pending_id,snap['pending']['modality'],trace)
                elif action=='confirm':
                    pending=snap['pending']
                    if len(pending['candidates'])==1:
                        result=self.choose_report(session_id,owner,pending['candidates'][0]['id'],pending['modality'],trace)
                    else:result={'kind':'clarification','message':'Please choose a specific patient. A yes alone cannot resolve this selection.','evidence':[]}
                elif action=='decline':
                    with self.factory.begin() as db:
                        s=db.get(store.Conversation,session_id)
                        s.pending_json=json.dumps({'candidates':[],'modality':snap['pending']['modality']})
                        s.context_version+=1
                    result={'kind':'clarification','message':'Okay, I will not open that patient’s report. Say the patient’s name again or choose a patient from the directory.','evidence':[]}
                elif action=='retrieve':
                    contextual_reference=bool(re.search(r'\b(her|his|their|selected|current)\b',command.text,re.I))
                    name=plan['patient_name'] or (snap['patient']['name'] if snap['patient'] and not snap['pending'] and contextual_reference else '')
                    result=self.retrieve(session_id,owner,name,plan['modality'],trace) if name else {'kind':'clarification','message':'Which patient should I find?','evidence':[]}
                elif action=='dictate':
                    if snap['pending']:result={'kind':'clarification','message':'Resolve the pending patient selection before creating a draft.','evidence':[]}
                    else:
                        raw=await self.ai.extract(command.text)
                        Extraction.model_validate(raw)
                        findings=validate_findings(command.text,raw['findings'])
                        draft_id=uid()
                        correction=re.search(r'\bcorrection\b[,\s:]*',command.text,re.I)
                        corrections=[] if not correction else [{'marker_start':correction.start(),'superseded_text':command.text[:correction.start()].strip(),'corrected_text':command.text[correction.end():].split('.')[0].strip()}]
                        body={'source_transcript':command.text,'findings':findings,'corrections':corrections,'readable_report':' '.join(dict.fromkeys(f['evidence'] for f in findings)),'requires_clinician_review':True}
                        with self.factory.begin() as db:db.add(store.Draft(id=draft_id,session_id=session_id,patient_id=snap['patient']['id'] if snap['patient'] else None,body_json=json.dumps(body),status='preview',version=1))
                        trace.append({'tool':'extract_findings','arguments':{'source':'current transcript'}})
                        result={'kind':'draft','message':'Draft prepared. Review the source, findings and uncertainty before saving.','draft':{'id':draft_id,'version':1,'status':'preview','patient_id':snap['patient']['id'] if snap['patient'] else None,**body},'evidence':[]}
                elif action in ('summarize','summarize_all','question'):
                    matches=self.question_identity_matches(command.text,plan['patient_name'])
                    if snap['pending'] or not snap['patient']:
                        result={'kind':'clarification','message':'Select one patient report before asking a contextual follow-up.','evidence':[]}
                    elif matches is not None and (len(matches)!=1 or matches[0]['id']!=snap['patient']['id']):
                        names=', '.join(p['name'] for p in matches)
                        message=(f'That name is ambiguous ({names}). Say the full patient name before I answer.' if len(matches)>1 else f'The selected patient is {snap["patient"]["name"]}. Open {names or "the intended patient"}’s report before asking about it.')
                        result={'kind':'clarification','message':message,'evidence':[]}
                    elif snap['report'] and any(re.search(r'\b'+m+r'\b',command.text,re.I) and m!=snap['report']['modality'] for m in ['OPG','CBCT','IOPA']) and not all_reports_requested(command.text):
                        result={'kind':'clarification','message':f'The selected report is {snap["report"]["modality"]}. Open the requested modality before asking about its findings.','evidence':[]}
                    elif all_reports_requested(command.text):
                        result=await self.summarize_patient_reports(session_id,snap,command.text,trace)
                    elif action=='summarize_all':
                        result={'kind':'clarification','message':'Do you want a summary of all reports for the selected patient, or only the selected report?','evidence':[]}
                    elif not snap['report']:
                        result={'kind':'clarification','message':'Select one patient report before asking a contextual follow-up.','evidence':[]}
                    else:
                        report=snap['report'];raw=await self.ai.answer(command.text,report,action=='summarize',self.recent_dialogue(session_id,snap))
                        answer=compose_answer(command.text,report,raw['claims'],action=='summarize')
                        trace.append({'tool':'summarize_report' if action=='summarize' else 'answer_from_report','arguments':{'report_id':report['id']}})
                        result={'kind':'answer',**answer}
                elif snap['pending']:
                    candidates=snap['pending']['candidates']
                    message=('Please say the full name, a unique surname, or choose a patient: '+', '.join(p['name'] for p in candidates)+'. I will keep your original report request.' if candidates else 'Say just the corrected full name or patient ID, or select a patient from the directory. I still have your original report request.')
                    if len(candidates)==1:message=f'Did you mean {candidates[0]["name"]}, patient {candidates[0]["id"]}? Say yes or no, or choose below.'
                    result={'kind':'candidates' if candidates else 'clarification','message':message,'candidates':candidates,'evidence':[]}
                else:result={'kind':'clarification','message':'Ask me to open a patient report, summarize the selected report, or switch to Dictation to prepare a draft.','evidence':[]}
            except ProviderError as e:
                result={'kind':'error','code':e.code,'message':e.message,'evidence':[]}
            except HTTPException as e:
                result={'kind':'validation','message':e.detail,'evidence':[]}
            result=self.envelope(session_id,owner,result,trace,turn_id,round((time.perf_counter()-start)*1000))
            with self.factory.begin() as db:db.get(store.Turn,turn_id).response_json=json.dumps(result)
            self.audit(session_id,'turn.completed',{'turn_id':turn_id,'kind':result['kind'],'elapsed_ms':result['elapsed_ms'],'mode':self.ai.config.mode})
            return result

    def get_draft(self, draft_id, owner):
        with self.factory() as db:
            draft=db.get(store.Draft,draft_id)
            if not draft:raise HTTPException(404,'Draft not found.')
        self.owned(draft.session_id,owner)
        return {'id':draft.id,'session_id':draft.session_id,'patient_id':draft.patient_id,'version':draft.version,'status':draft.status,**json.loads(draft.body_json)}

    async def edit_draft(self, draft_id, owner, edit):
        old=self.get_draft(draft_id,owner)
        async with self.locks.setdefault(old['session_id'],asyncio.Lock()):
            with self.factory.begin() as db:
                d=db.get(store.Draft,draft_id)
                if d.version!=edit.version:raise HTTPException(409,'Draft changed. Reload before editing.')
                body=json.loads(d.body_json)
                findings=validate_findings(body['source_transcript'],[f.model_dump() for f in edit.findings])
                body.update(findings=findings,readable_report=' '.join(dict.fromkeys(f['evidence'] for f in findings)))
                db.add(store.DraftRevision(id=uid(),draft_id=d.id,version=d.version,body_json=d.body_json))
                d.body_json=json.dumps(body);d.version+=1;d.status='preview'
            return self.get_draft(draft_id,owner)

    async def save_draft(self, draft_id, owner, version):
        old=self.get_draft(draft_id,owner)
        async with self.locks.setdefault(old['session_id'],asyncio.Lock()):
            snap=self.snapshot(old['session_id'],owner)
            if not snap['patient'] or snap['pending']:raise HTTPException(422,'Select one patient before saving a draft.')
            with self.factory.begin() as db:
                d=db.get(store.Draft,draft_id)
                if d.version!=version:raise HTTPException(409,'Draft changed. Reload before saving.')
                if d.patient_id and d.patient_id!=snap['patient']['id']:raise HTTPException(409,'This draft belongs to a different patient. Return to that patient before saving.')
                d.patient_id=snap['patient']['id'];d.status='saved_draft';d.version+=1
            self.audit(old['session_id'],'draft.saved',{'draft_id':draft_id})
            return self.get_draft(draft_id,owner)
