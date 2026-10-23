import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Activity,ArrowDownToLine,ArrowRight,AudioLines,Check,ChevronRight,Code2,FileText,FolderOpen,Headphones,History,LoaderCircle,MessageSquare,Mic,Pause,Search,Send,ShieldCheck,Square,Volume2,X} from 'lucide-react';
import {startVoice,type VoiceHandle} from './voice';
import './style.css';

type Patient={id:string;name:string;reference:string};
type Report={id:string;patient_id:string;modality:string;performed_at:string;version:number;content:string};
type Session={id:string;context_version:number;patient:Patient|null;report:Report|null;pending:any;mode:string};
type Finding={observation:string;anatomical_site:string;polarity:string;certainty:string;evidence:string};
type Draft={id:string;version:number;status:string;patient_id:string|null;source_transcript:string;findings:Finding[];readable_report:string;requires_clinician_review:boolean};
type ReportSection={title:string;paragraphs:string[]};
function reportSections(content:string):ReportSection[]{
  return content.split(/\n\n+/).map(block=>{const lines=block.split('\n');return /^[A-Z ]+:$/.test(lines[0])?{title:lines[0].slice(0,-1),paragraphs:lines.slice(1)}:{title:'Findings',paragraphs:[block]};});
}
type Message={role:'user'|'assistant';text:string;result?:any};
const cleanFindings=(findings:Finding[])=>findings.map(({observation,anatomical_site,polarity,certainty,evidence})=>({observation,anatomical_site,polarity,certainty,evidence}));
const examples=['Open Priya’s latest OPG report','Summarize her report','Open Meera Iyer’s latest OPG report'];
const dictations=['Lower right third molar is horizontally impacted. No evidence of a fracture.','Possible periapical radiolucency near the upper left first molar. Further assessment is required.','Upper right second molar. Correction, upper left second molar. No definite caries identified.'];
async function api(url:string,body?:unknown,method='POST'){
  const response=await fetch('/api'+url,{cache:'no-store',credentials:'include',method:body===undefined?'GET':method,headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok){let detail;try{detail=(await response.json()).detail;}catch{detail='Request failed.';}throw new Error(typeof detail==='string'?detail:JSON.stringify(detail));}
  return response.json();
}
function App(){
  const [config,setConfig]=useState<any>(null),[session,setSession]=useState<Session|null>(null),[patients,setPatients]=useState<Patient[]>([]),[ready,setReady]=useState(false);
  const [messages,setMessages]=useState<Message[]>([]),[input,setInput]=useState(''),[query,setQuery]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [tab,setTab]=useState<'report'|'draft'>('report'),[intent,setIntent]=useState<'auto'|'dictate'>('auto'),[draft,setDraft]=useState<Draft|null>(null),[findings,setFindings]=useState<Finding[]>([]),[showJson,setShowJson]=useState(false);
  const [drafts,setDrafts]=useState<Draft[]>([]),[jsonText,setJsonText]=useState('[]'),[autoEnd,setAutoEnd]=useState(true);
  const [draftFeedback,setDraftFeedback]=useState<{type:'pending'|'success'|'error';text:string}|null>(null);
  const [voiceState,setVoiceState]=useState('idle'),[partial,setPartial]=useState(''),[speech,setSpeech]=useState(true),[speaking,setSpeaking]=useState(false),[evidence,setEvidence]=useState<any>(null),[speechStatus,setSpeechStatus]=useState('');
  const voice=useRef<VoiceHandle|null>(null),audio=useRef<HTMLAudioElement|null>(null),audioUrl=useRef(''),browserUtterance=useRef<SpeechSynthesisUtterance|null>(null),speechContext=useRef<AudioContext|null>(null),speechSource=useRef<AudioBufferSourceNode|null>(null),generation=useRef(0),voiceGeneration=useRef(0),bottom=useRef<HTMLDivElement>(null),reportBody=useRef<HTMLDivElement>(null);
  const blocked=busy||voiceState!=='idle'||!ready||!session;
  const draftDirty=!!draft&&JSON.stringify(cleanFindings(findings))!==JSON.stringify(cleanFindings(draft.findings));
  const draftSaved=!!draft&&draft.status==='saved_draft'&&!draftDirty;
  useEffect(()=>{void (async()=>{try{
    setConfig(await api('/config'));let s;const old=sessionStorage.getItem('viscan-session');try{s=old?await api('/sessions/'+old):null;}catch{}
    s=s||await api('/sessions',{});setSession(s);sessionStorage.setItem('viscan-session',s.id);setPatients(await api('/patients'));
    const history=await api('/sessions/'+s.id+'/history');setMessages(history.messages);setDrafts(history.drafts);
    const active=history.drafts.find((d:Draft)=>d.id===sessionStorage.getItem('viscan-active-draft'))||history.drafts.at(-1);
    if(active){setDraft(active);setFindings(active.findings);}
    const editor=sessionStorage.getItem('viscan-editor-'+s.id);
    if(editor){try{const saved=JSON.parse(editor);if(active&&saved.draftId===active.id&&saved.version===active.version){setFindings(saved.findings);setInput(saved.input||'');}}catch{}}
  }catch(e){setError((e as Error).message);}finally{setReady(true);}})();return()=>{voiceGeneration.current++;voice.current?.cancel();audio.current?.pause();speechSource.current?.stop();if('speechSynthesis' in window)window.speechSynthesis.cancel();void speechContext.current?.close();};},[]);
  useEffect(()=>{reportBody.current?.scrollTo({top:0});},[session?.report?.id,session?.report?.version,tab]);
  useEffect(()=>{setJsonText(JSON.stringify(cleanFindings(findings),null,2));},[findings]);
  useEffect(()=>{setDraftFeedback(null);},[draft?.id]);
  useEffect(()=>{if(session&&draft)sessionStorage.setItem('viscan-editor-'+session.id,JSON.stringify({draftId:draft.id,version:draft.version,findings,input}));},[findings,input,draft,session]);
  useEffect(()=>{bottom.current?.scrollIntoView({behavior:'smooth',block:'nearest'});},[messages,partial]);
  function unlockSpeech(){if(!speechContext.current)speechContext.current=new AudioContext();if(speechContext.current.state==='suspended')void speechContext.current.resume().catch(()=>{});}
  function stopSpeech(){generation.current++;if('speechSynthesis' in window)window.speechSynthesis.cancel();browserUtterance.current=null;if(speechSource.current){speechSource.current.onended=null;speechSource.current.stop();speechSource.current=null;}setSpeechStatus('');audio.current?.pause();audio.current=null;if(audioUrl.current)URL.revokeObjectURL(audioUrl.current);setSpeaking(false);}
  async function browserReply(text:string,current:number){
    if(!text||!('speechSynthesis' in window))return false;
    const synthesis=window.speechSynthesis;
    if(!synthesis.getVoices().length)await new Promise<void>(resolve=>{
      const done=()=>{clearTimeout(timer);synthesis.removeEventListener('voiceschanged',done);resolve();};
      const timer=setTimeout(done,1000);synthesis.addEventListener('voiceschanged',done,{once:true});
    });
    if(current!==generation.current)return true;
    const voices=synthesis.getVoices();if(!voices.length)return false;
    const utterance=new SpeechSynthesisUtterance(text);browserUtterance.current=utterance;
    utterance.voice=voices.find(v=>v.lang.toLowerCase()==='en-in')||voices.find(v=>v.lang.toLowerCase().startsWith('en'))||voices[0];
    utterance.lang=utterance.voice.lang;
    const status='Browser voice — cloud speech unavailable';setSpeechStatus(status);
    utterance.onstart=()=>{if(current===generation.current){setSpeaking(true);setSpeechStatus(status);}};
    utterance.onend=()=>{if(current===generation.current){setSpeaking(false);setSpeechStatus('Browser voice used — cloud speech unavailable');}};
    utterance.onerror=()=>{if(current===generation.current){setSpeaking(false);setSpeechStatus('Spoken reply unavailable — use Listen to retry.');setError('Browser speech could not play. The text response remains available.');}};
    synthesis.speak(utterance);return true;
  }
  async function play(turnId:string,text=''){
    if(!session)return;unlockSpeech();stopSpeech();const current=generation.current;
    try{
      setSpeaking(true);setSpeechStatus('Preparing spoken reply…');const r=await fetch(`/api/sessions/${session.id}/speech`,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({turn_id:turnId})});
      if(!r.ok)throw new Error('Speech unavailable. The text response remains available.');
      const blob=await r.blob();if(current!==generation.current)return;
      const url=URL.createObjectURL(blob);audioUrl.current=url;const player=new Audio(url);audio.current=player;
      const ended=()=>{if(current===generation.current){setSpeaking(false);setSpeechStatus('');}URL.revokeObjectURL(url);};player.onended=ended;player.onerror=()=>{if(current===generation.current){setSpeaking(false);setSpeechStatus('Spoken reply unavailable — use Listen to retry.');setError('Audio playback failed. Use Listen to retry the spoken reply.');}};
      try{await player.play();if(current===generation.current)setSpeechStatus('Speaking…');}
      catch(playError){
        if((playError as DOMException).name!=='NotAllowedError')throw playError;
        const context=speechContext.current;if(!context||context.state!=='running')throw new Error('Your browser paused audio. Click Listen to enable the spoken reply.');
        const decoded=await context.decodeAudioData(await blob.arrayBuffer());if(current!==generation.current)return;
        const source=context.createBufferSource();source.buffer=decoded;source.connect(context.destination);source.onended=ended;speechSource.current=source;source.start();setSpeechStatus('Speaking…');
      }
    }catch(e){if(current===generation.current){if(await browserReply(text,current))return;setSpeaking(false);setSpeechStatus('Spoken reply unavailable — use Listen to retry.');setError((e as Error).message);}}
  }
  function accept(result:any){
    setSession(result.session);setEvidence(null);if(result.session.pending)setTab('report');setMessages(m=>[...m,{role:'assistant',text:result.message,result}]);
    if(result.draft){setDraft(result.draft);setFindings(result.draft.findings);setDrafts(old=>[...old.filter(d=>d.id!==result.draft.id),result.draft]);sessionStorage.setItem('viscan-active-draft',result.draft.id);setTab('draft');}
    if(result.report){setTab('report');setEvidence(null);}
    if(speech&&result.turn_id&&config?.mode==='live')void play(result.turn_id,result.speech_text||result.message);
  }
  async function submit(text=input,override?:'auto'|'dictate'){
    if(!session||busy||!text.trim())return;if(speech)unlockSpeech();stopSpeech();setError('');setInput('');setPartial('');setBusy(true);setMessages(m=>[...m,{role:'user',text}]);
    try{accept(await api(`/sessions/${session.id}/commands`,{text,utterance_id:crypto.randomUUID(),context_version:session.context_version,intent:override||intent}));}
    catch(e){setError((e as Error).message);try{setSession(await api('/sessions/'+session.id));}catch{}}
    finally{setBusy(false);}
  }
  async function select(patientId:string){
    if(!session)return;if(speech)unlockSpeech();stopSpeech();setBusy(true);setError('');
    setMessages(old=>[...old,{role:'user',text:'Selected patient '+patientId}]);
    try{accept(await api(`/sessions/${session.id}/selection`,{patient_id:patientId,context_version:session.context_version}));}catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  async function newSession(){
    stopSpeech();setBusy(true);setError('');
    try{const fresh=await api('/sessions',{});setSession(fresh);sessionStorage.setItem('viscan-session',fresh.id);sessionStorage.removeItem('viscan-active-draft');setMessages([]);setDraft(null);setDrafts([]);setFindings([]);setInput('');setPartial('');setEvidence(null);setTab('report');setIntent('auto');}
    catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  async function record(){
    if(!session)return;
    if(voiceState!=='idle'){voice.current?.stop();setVoiceState('finishing');return;}
    if(speech)unlockSpeech();stopSpeech();setError('');setPartial('');setVoiceState('connecting');const capture=++voiceGeneration.current;
    try{const handle=await startVoice(session.id,event=>{
      if(capture!==voiceGeneration.current)return;
      if(event.type==='voice.ready')setVoiceState('listening');
      if(event.type==='voice.finalizing')setVoiceState('finishing');
      if(event.type==='voice.cancelled')setVoiceState('idle');
      if(event.type==='transcript.partial'||event.type==='transcript.segment')setPartial(event.text);
      if(event.type==='transcript.final'){setVoiceState('idle');voice.current=null;void submit(event.text);}
      if(event.type==='error'){setVoiceState('idle');voice.current=null;setError(event.message);}
    },autoEnd);if(capture!==voiceGeneration.current){handle.cancel();return;}voice.current=handle;}catch{if(capture===voiceGeneration.current){setVoiceState('idle');setError('Microphone unavailable. Allow microphone access or type your transcript.');}}
  }
  function cancelVoice(){voiceGeneration.current++;voice.current?.cancel();voice.current=null;setVoiceState('idle');setPartial('');}
  async function saveDraft(){
    if(!draft||busy||draftSaved)return;setBusy(true);setError('');setDraftFeedback({type:'pending',text:'Saving reviewed draft…'});
    try{const edited=await api('/drafts/'+draft.id,{version:draft.version,findings:cleanFindings(findings)},'PATCH');const saved=await api('/drafts/'+draft.id+'/save',{version:edited.version});setDraft(saved);setFindings(saved.findings);setDrafts(old=>old.map(d=>d.id===saved.id?saved:d));setDraftFeedback({type:'success',text:`Saved as draft · v${saved.version}. Clinician review is still required.`});}
    catch(e){const message=(e as Error).message;setError(message);setDraftFeedback({type:'error',text:'Could not save: '+message});try{const fresh=await api('/drafts/'+draft.id);setDraft(fresh);}catch{}}finally{setBusy(false);}
  }
  function updateFinding(index:number,key:keyof Finding,value:string){setDraftFeedback(null);setFindings(old=>old.map((f,i)=>i===index?{...f,[key]:value}:f));}
  async function applyJson(){
    if(!draft)return;setBusy(true);setError('');setDraftFeedback(null);
    try{const parsed=JSON.parse(jsonText);if(!Array.isArray(parsed))throw new Error('JSON must be an array of findings.');const edited=await api('/drafts/'+draft.id,{version:draft.version,findings:parsed},'PATCH');setDraft(edited);setFindings(edited.findings);setDrafts(old=>old.map(d=>d.id===edited.id?edited:d));}
    catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  async function exportDraft(){
    if(!draft)return;setBusy(true);setError('');setDraftFeedback(null);
    try{const edited=await api('/drafts/'+draft.id,{version:draft.version,findings:cleanFindings(findings)},'PATCH');setDraft(edited);setFindings(edited.findings);setDrafts(old=>old.map(d=>d.id===edited.id?edited:d));const url=URL.createObjectURL(new Blob([JSON.stringify(edited,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`synthetic-draft-${draft.id}.json`;a.click();URL.revokeObjectURL(url);}
    catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  return <div className="app">
    <nav className="rail" aria-label="Main navigation"><div className="brand-symbol"><Activity size={25}/></div><button className="rail-active" title="Clinical workspace"><FolderOpen size={21}/></button><a href="/docs" title="API documentation"><Code2 size={21}/></a><div className="rail-bottom"><ShieldCheck size={22}/><span className="avatar">SC</span></div></nav>
    <div className="shell"><header className="topbar"><div className="header-brand"><span className="heartbeat-logo" aria-hidden="true"><Activity size={28} strokeWidth={1.8}/></span><div className="wordmark">VI<span>SCAN</span><small>CLINICAL ASSISTANT</small><small className="build-id">Build {config?.build_id||'loading'}</small></div></div><div className="top-links"><button className="new-session" disabled={blocked} onClick={()=>void newSession()}><History size={13}/> New session</button><span className="synthetic"><ShieldCheck size={14}/> Synthetic data only</span><span className={'mode '+(config?.mode==='live'?'live':'')}><i/>{config?.mode==='live'?'Live providers':'Fixture mode'}</span><span className="demo-user">Demo clinician <span className="avatar small">SC</span></span></div></header>
    <div className="page-heading"><div><div className="eyebrow">DENTAL INTELLIGENCE WORKSPACE</div><h1>Patient reports & dictation</h1><p>1. Open a patient report   ·   2. Ask about it or create a draft   ·   3. Review and save</p></div><div className="workspace-note"><span className="pulse"/>Clinician review required<br/><small>Every generated report remains a draft.</small></div></div>
    {config?.mode==='fixture'&&<div className="fixture-banner"><Code2 size={16}/><span><b>Reproducible fixture mode.</b> Sample dictations and report summaries work without API keys. Microphone and free-form questions require live mode.</span></div>}
    {error&&<div className="error" role="alert"><span>{error}</span><button aria-label="Dismiss error" onClick={()=>setError('')}><X size={17}/></button></div>}
    <main className="workspace">
      <aside className="patients"><div className="panel-heading"><h2>Patients</h2><span className="count">{patients.length}</span></div><label className="search"><Search size={15}/><input aria-label="Search synthetic patients" placeholder="Search patients" value={query} onChange={e=>setQuery(e.target.value)}/></label><div className="list-caption">SYNTHETIC DIRECTORY</div>
        <div className="patient-list">{patients.filter(p=>p.name.toLowerCase().includes(query.toLowerCase())).map(p=><button key={p.id} disabled={blocked} onClick={()=>void submit(`Open ${p.name}'s latest report`,'auto')} className={'patient '+(!session?.pending&&session?.patient?.id===p.id?'selected':'')}><span className="patient-avatar">{p.name.split(' ').map(n=>n[0]).join('')}</span><span><b>{p.name}</b><small>{p.id} · {p.reference}</small></span><ChevronRight size={14}/></button>)}</div>
        <div className="directory-note"><ShieldCheck size={18}/><p>Fictional identities.<br/>No real patient information.</p></div>
      </aside>
      <section className="record-panel"><div className={'active-context '+(session?.pending?'needs-confirmation':'')} aria-label="Active patient context"><small>{session?.pending?(session.pending.candidates.length?'PATIENT CONFIRMATION REQUIRED':'PATIENT NAME NEEDED'):'ACTIVE PATIENT'}</small><strong>{session?.pending?'Resolve the requested patient below':session?.patient?.name||'No patient selected'}</strong><span>{session?.pending?(session.report?'Previous report is paused':'Your report request is waiting'):session?.report?`${session.report.modality} · ${session.report.id}`:'Select a patient or use the assistant'}</span></div><div className="record-tabs"><button className={tab==='report'?'active':''} onClick={()=>setTab('report')}><FileText size={16}/> Report</button><button className={tab==='draft'?'active':''} onClick={()=>setTab('draft')}><AudioLines size={16}/> Draft editor {draft&&<i/>}</button><span className="context-version">Context v{session?.context_version||0}</span></div>
      {evidence&&<section className="evidence-preview" aria-label="Cited source evidence"><button aria-label="Close source evidence" onClick={()=>setEvidence(null)}><X size={15}/></button><strong>{evidence.report_id} · revision {evidence.report_version}</strong><blockquote>{evidence.quote}</blockquote><small>Exact excerpt cited by the answer. Active patient selection is unchanged.</small></section>}
      {session?.pending?<div className="identity-resolution" role="region" aria-label="Confirm patient identity"><ShieldCheck size={28}/><h2>{session.pending.candidates.length===0?'What is the patient’s correct name?':session.pending.candidates.length===1?`Did you mean ${session.pending.candidates[0].name}, patient ${session.pending.candidates[0].id}?`:'Which patient did you mean?'}</h2><p>{session.pending.candidates.length===0?'I could not match the name. Say just the corrected full name or patient ID; you do not need to repeat the report request.':session.pending.candidates.length===1?'Say yes or no, say the correct full name, or choose below.':'More than one patient matches your request. Say the intended name or choose below.'}</p><div className="identity-options">{session.pending.candidates.map((p:Patient)=><button className="secondary" key={p.id} disabled={blocked} onClick={()=>void select(p.id)}><span><b>{p.name}</b><small>{p.id} · {p.reference}</small></span><span>Confirm & open <ArrowRight size={15}/></span></button>)}</div><p className="small-note">You can also select a patient in the directory or edit and resend your request. The previous report cannot be used for follow-ups while this is unresolved.</p></div>:tab==='report'?(session?.report?<div className="record-content" ref={reportBody}><div className="record-title"><div><div className="eyebrow">SELECTED PATIENT</div><h2>{session.patient?.name}</h2><span>{session.patient?.id} <span className="separator">/</span> {session.patient?.reference}</span></div><span className="modality">{session.report.modality}</span></div>
        {session.pending&&<div className="warning">Patient selection is pending. Resolve it in the assistant before using this report as context.</div>}
        <div className="report-meta"><div><small>EXAMINATION</small><b>{session.report.modality==='OPG'?'Orthopantomogram':session.report.modality==='CBCT'?'Cone beam CT':'Intraoral radiograph'}</b></div><div><small>PERFORMED</small><b>{new Date(session.report.performed_at).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'})}</b></div></div>
        <div className="source-label"><span className="source-dot"/>SOURCE REPORT <small>{session.report.id} · revision {session.report.version}</small></div>
        <div className="report-document">{reportSections(session.report.content).map((section,i)=><section className={'document-section '+(section.title==='IMPRESSION'?'impression':'')} key={i}><h3>{section.title.toLowerCase().replace(/\b\w/g,c=>c.toUpperCase())}</h3>{section.paragraphs.map((paragraph,j)=><p className={evidence?.report_id===session.report?.id&&evidence?.report_version===session.report?.version&&evidence?.quote.includes(paragraph)?'highlight':''} key={j}>{paragraph}</p>)}</section>)}</div>
        <div className="review-note"><ShieldCheck size={20}/><div><b>Evidence first, clinician always.</b><p>This is a synthetic text report. The assistant retrieves and structures text; it does not interpret dental images.</p></div></div>
        <button className="text-button" disabled={blocked} onClick={()=>void submit('Summarize her report','auto')}>Summarize this report <ArrowRight size={15}/></button>
      </div>:<div className="welcome"><div className="welcome-icon"><FolderOpen size={34}/></div><div className="eyebrow">YOUR CLINICAL CONTEXT STARTS HERE</div><h2>A report, one request away.</h2><p>Select a fictional patient or ask the assistant to find a report. Similar names always require a clear selection.</p><button className="primary" disabled={blocked} onClick={()=>void submit('Open Priya’s latest OPG report','auto')}>Try a voice-ready request <ArrowRight size={16}/></button><div className="welcome-steps"><span><b>01</b> Resolve identity</span><span><b>02</b> Inspect evidence</span><span><b>03</b> Review the draft</span></div></div>):
      <div className="record-content draft-content"><div className="record-title"><div><div className="eyebrow">CLINICAL DICTATION</div><h2>From observation to draft.</h2><span>{draft?'Review source-linked findings before saving.':'Speak or type observations. Keep the clinician in control.'}</span></div><span className="draft-badge">DRAFT</span></div>
        {drafts.length>0&&<label className="draft-selector">SESSION DRAFTS<select aria-label="Restore a session draft" value={draft?.id||''} disabled={blocked} onChange={e=>{const selected=drafts.find(d=>d.id===e.target.value);if(selected){setDraft(selected);setFindings(selected.findings);sessionStorage.setItem('viscan-active-draft',selected.id);}}}>{drafts.map((d,i)=><option key={d.id} value={d.id}>Draft {i+1} · {d.patient_id||'Unassigned'} · {d.status==='saved_draft'?'saved':'preview'}</option>)}</select></label>}
        {!draft?<><div className="dictation-intro"><Mic size={28}/><h3>Capture what you observe.</h3><p>Choose a sample below or switch the assistant to Dictation. Nothing becomes a signed report.</p></div>{dictations.map((s,i)=><button className="sample-dictation" key={s} disabled={blocked} onClick={()=>{setIntent('dictate');void submit(s,'dictate');}}><span>0{i+1}</span><p>{s}</p><ArrowRight size={16}/></button>)}</>:<><div className="draft-status"><span><ShieldCheck size={15}/>{draftSaved?'Saved as draft · review still required':draftDirty?'Unsaved edits · clinician review required':'Unsaved preview · clinician review required'}</span><small>v{draft.version}</small></div><label className="field-label">SOURCE TRANSCRIPT</label><blockquote className="transcript-source">{draft.source_transcript}</blockquote>
        <div className="section-label"><h3>Structured findings</h3><button className="text-button" onClick={()=>setShowJson(!showJson)}><Code2 size={14}/>{showJson?'Hide JSON':'View JSON'}</button></div>
        {findings.map((f,i)=><div className="finding-editor" key={i}><div className="finding-editor-head"><span>FINDING {String(i+1).padStart(2,'0')}</span><span className={'certainty '+(f.certainty!=='asserted'?'uncertain':'')}>{f.certainty.replace('_',' ')}</span></div><label>Observation<input value={f.observation} onChange={e=>updateFinding(i,'observation',e.target.value)}/></label><label>Anatomical site<input value={f.anatomical_site} onChange={e=>updateFinding(i,'anatomical_site',e.target.value)}/></label><div className="two-fields"><label>Polarity<select value={f.polarity} onChange={e=>updateFinding(i,'polarity',e.target.value)}><option>present</option><option>negated</option><option>unspecified</option></select></label><label>Certainty<select value={f.certainty} onChange={e=>updateFinding(i,'certainty',e.target.value)}><option>asserted</option><option>uncertain</option><option>not_definite</option></select></label></div><small className="quoted-evidence">Source: “{f.evidence}”</small></div>)}
        <section className="readable-draft"><h3>Readable draft report</h3><p>{Array.from(new Set(findings.map(f=>f.evidence))).join(' ')}</p><small>Draft derived from source evidence. Clinician review is required.</small></section>
        {showJson&&<div className="json-editor"><label htmlFor="findings-json">EDITABLE FINDINGS JSON</label><textarea id="findings-json" aria-label="Editable findings JSON" value={jsonText} onChange={e=>setJsonText(e.target.value)} spellCheck={false}/><button className="secondary" disabled={blocked} onClick={()=>void applyJson()}>Validate & apply JSON</button><small>Source transcript and review status cannot be overridden through JSON.</small></div>}<section className="draft-save-area" aria-label="Draft saving"><div className="draft-actions"><button className="secondary" disabled={blocked} onClick={()=>void exportDraft()}><ArrowDownToLine size={15}/> Export JSON</button><button className="primary" disabled={blocked||draftSaved} onClick={()=>void saveDraft()}>{draftFeedback?.type==='pending'?<LoaderCircle className="spin" size={15}/>:<Check size={15}/>} {draftFeedback?.type==='pending'?'Saving…':draftSaved?'Saved as draft':'Save reviewed draft'}</button></div>{(draftFeedback||draftSaved)&&<div className={'draft-save-feedback '+(draftFeedback?.type||'success')} role={draftFeedback?.type==='error'?'alert':'status'}>{draftFeedback?.text||`Saved as draft · v${draft.version}. Clinician review is still required.`}</div>}<small>Unspecified details can stay unspecified. Review the generated findings; add only details supported by your transcript.</small></section><p className="small-note">Saving does not sign or finalize this report. Edits must remain supported by the source transcript.</p></>}
      </div>}</section>
      <aside className="assistant-panel"><div className="assistant-header"><span className="assistant-mark"><AudioLines size={19}/></span><div><h2>Clinical assistant</h2><small>Find reports · Ask questions · Dictate findings</small></div><span className="online-dot"/></div>
        <div className="chat-messages"><div className="assistant-intro"><span className="eyebrow">READY WHEN YOU ARE</span><h3>What would you like to do?</h3><p>I can find patient reports, summarize the source, and structure your dictated observations.</p></div>
        {messages.length===0&&<div className="suggestions">{examples.map(s=><button disabled={blocked} key={s} onClick={()=>void submit(s,'auto')}><MessageSquare size={14}/><span>{s}</span><ArrowRight size={14}/></button>)}</div>}
        {messages.map((m,i)=><div className={'message '+m.role} key={i}><small>{m.role==='user'?'YOU':'VI-SCAN'}{m.result?.mode==='fixture'?' · FIXTURE':''}</small><p>{m.text}</p>{m.role==='user'&&<button className="edit-request" disabled={blocked} onClick={()=>{setInput(m.text);setIntent('auto');}}>Edit request</button>}{m.result?.candidates&&<div className="candidate-list">{m.result.candidates.map((p:Patient)=><button key={p.id} disabled={blocked||!session?.pending?.candidates?.some((candidate:Patient)=>candidate.id===p.id)} onClick={()=>void select(p.id)}><b>{p.name}</b><span>{p.id} <ArrowRight size={14}/></span></button>)}</div>}
        {!!m.result?.evidence?.length&&<div className="citations">{m.result.evidence.map((e:any,j:number)=><button key={j} onClick={()=>{setEvidence(e);setTab('report');}}><FileText size={12}/>{e.report_id} · source {j+1}</button>)}</div>}
        {m.result?.trace?.length>0&&<details className="tool-trace"><summary>{m.result.trace.length} verified tool step{m.result.trace.length>1?'s':''} · {m.result.elapsed_ms?`${(m.result.elapsed_ms/1000).toFixed(1)}s`:'ready'}</summary>{m.result.trace.map((t:any,j:number)=><code key={j}>{t.tool}({JSON.stringify(t.arguments)})</code>)}</details>}
        {m.result?.turn_id&&config?.mode==='live'&&<button className="speak-button" disabled={busy} onClick={()=>void play(m.result.turn_id,m.result.speech_text||m.text)}><Volume2 size={13}/> {m.result?.speech_text?'Listen to overview':'Listen'}</button>}</div>)}
        {busy&&<div className="thinking"><LoaderCircle className="spin" size={15}/> Checking context and evidence…</div>}{partial&&<div className="partial"><AudioLines size={16}/><p>{partial}</p><small>{voiceState==='finishing'?'Finalizing…':'Live transcript'}</small></div>}<div ref={bottom}/></div>
        <div className="composer">{speechStatus&&<div className="speech-status" role="status"><Volume2 size={14}/>{speechStatus}</div>}<div className="composer-modes"><button disabled={blocked} className={intent==='auto'?'active':''} onClick={()=>setIntent('auto')}>Find / ask</button><button disabled={blocked} className={intent==='dictate'?'active':''} onClick={()=>{setIntent('dictate');setTab('draft');}}>Create draft</button><label title="Automatically speak new responses"><input type="checkbox" checked={speech} disabled={config?.mode!=='live'} onChange={e=>{setSpeech(e.target.checked);if(e.target.checked)unlockSpeech();else stopSpeech();}}/><Headphones size={14}/> Spoken replies</label></div><textarea aria-label="Assistant request" value={input} onChange={e=>setInput(e.target.value)} placeholder={intent==='dictate'?'Dictate a clinical observation…':'Ask about a patient or report…'} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();if(!blocked)void submit();}}}/><div className="voice-options"><label title="Submit after approximately 1.6 seconds of silence once speech has started"><input type="checkbox" aria-label="Automatically finish after a pause" checked={autoEnd} disabled={blocked} onChange={e=>setAutoEnd(e.target.checked)}/> Auto-finish after a pause</label>{voiceState!=='idle'&&<button aria-label="Cancel recording" onClick={cancelVoice}>Cancel</button>}</div><div className="composer-actions"><button className={'mic-button '+(voiceState!=='idle'?'recording':'')} disabled={busy||config?.mode!=='live'||voiceState==='finishing'} onClick={()=>void record()} aria-label={voiceState==='idle'?'Start microphone':'Stop and submit microphone'}>{voiceState==='idle'?<Mic size={17}/>:<Square size={15}/>}<span>{voiceState==='idle'?'Speak a request':voiceState==='connecting'?'Connecting…':voiceState==='finishing'?'Finalizing…':'Stop & submit'}</span></button>{speaking&&<button className="icon-button" aria-label="Stop speech" onClick={stopSpeech}><Pause size={17}/></button>}<button className="send-button" aria-label="Send request" disabled={blocked||!input.trim()||!session} onClick={()=>void submit()}><Send size={17}/><span>Send</span></button></div><small className="composer-footnote">Synthetic data · source-linked answers · clinician review</small></div>
      </aside>
    </main><footer className="footer"><span><ShieldCheck size={13}/> Designed for traceability. Built for clinician control.</span><span>VI-SCAN technical proof of concept <span className="separator">/</span> No diagnostic imaging AI</span></footer>
    </div></div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
