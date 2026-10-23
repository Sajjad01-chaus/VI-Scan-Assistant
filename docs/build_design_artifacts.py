"""Build portable design diagrams and a one-page reviewer architecture PDF."""
from pathlib import Path
from html import escape
import re

ROOT=Path(__file__).resolve().parent
DIAGRAMS=ROOT/'diagrams'
DIAGRAMS.mkdir(exist_ok=True)
INK='#172D42';MUTED='#536779';TEAL='#137D85';LINE='#D3DEE5';BG='#F5F8FA';WHITE='#FFFFFF'

def text(x,y,value,size=18,color=INK,weight=400):
    return f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(value)}</text>'

def box(x,y,w,h,title,lines,accent=False):
    parts=[f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{WHITE}" stroke="{TEAL if accent else LINE}" stroke-width="{2 if accent else 1}"/>',text(x+20,y+32,title,20,TEAL if accent else INK,600)]
    for i,line in enumerate(lines):parts.append(text(x+20,y+61+i*25,line,16,MUTED))
    return ''.join(parts)

def arrow(x1,y1,x2,y2,label=None,both=False):
    start=' marker-start="url(#arrow)"' if both else ''
    parts=[f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{TEAL}" stroke-width="2" marker-end="url(#arrow)"{start}/>']
    if label:parts.append(text((x1+x2)/2-12,(y1+y2)/2-8,label,12,MUTED))
    return ''.join(parts)

def svg(name,title,subtitle,body,w=1440,h=1050):
    s=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}"><defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8 Z" fill="{TEAL}"/></marker></defs><rect width="{w}" height="{h}" fill="{BG}"/>{text(44,44,title,28,INK,600)}{text(44,76,subtitle,16,MUTED)}{body}{text(44,h-24,'283 local tests | Synthetic data only | One worker; hosted inference | Historical voice evidence; current quota not guaranteed',14,MUTED)}</svg>'''
    (DIAGRAMS/f'{name}.svg').write_text(s,encoding='utf-8')

def component(x,y,w,h,title,lines,accent=False):
    parts=[f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{WHITE}" stroke="{TEAL if accent else LINE}" stroke-width="{2 if accent else 1}"/>',text(x+16,y+27,title,19,TEAL if accent else INK,600)]
    for i,line in enumerate(lines):parts.append(text(x+16,y+51+i*20,line,15,MUTED))
    return ''.join(parts)

body=''
for x,title in [(44,'BROWSER'),(430,'FASTAPI - ONE INSTANCE'),(860,'ADAPTERS'),(1040,'DATA / HOSTED MODELS')]:
    body+=text(x,123,title,15,MUTED,600)
body+=component(44,155,310,105,'Input capture',['AudioWorklet: 16 kHz mono PCM','Typed input bypasses STT','Final transcript -> HTTP command'])
body+=component(44,325,310,105,'Clinical workspace',['Patient / report / evidence / chat','Editable draft JSON; explicit save','Fixture mode: same rules, no cloud'])
body+=component(44,535,310,85,'Speech playback',['Text first; separate speech request','Cloud fail: browser voice or text'])
body+=component(430,155,400,80,'HTTP / WebSocket boundary',['Cookie ownership; input/context checks','WS transcribes; HTTP executes commands'])
body+=component(430,275,400,90,'Typed Python orchestration',['Local acknowledgement / pending reply','Otherwise: typed LLM plan or extraction'],True)
body+=component(430,405,400,90,'Business rules + operations',['Identity / modality scope; validate_findings','Quote, site, negation, uncertainty, versions'],True)
body+=component(430,535,400,85,'Evidence + response rendering',['Cited answer / editable draft JSON','Saved turn -> separate POST /speech'])
body+=component(1040,155,356,80,'Google streaming STT',['Partial / final transcript events','Fallback: Groq file STT'])
body+=component(1040,275,356,90,'Groq GPT-OSS 120B',['plan_assistant_action / extraction','Grounded answer; untrusted output'])
body+=component(1040,405,356,90,'SQLite + SQLAlchemy',['Patients, reports, sessions, drafts, audit','Alembic; versioned draft revisions'])
body+=component(1040,535,356,85,'Groq Orpheus TTS',['Saved reply or labeled overview','Cloud fallback: Google TTS'])
for y,label in [(171,'STT adapter'),(296,'LLM adapter'),(554,'TTS adapter')]:
    body+=f'<rect x="860" y="{y}" width="140" height="48" rx="7" fill="#E9F3F2" stroke="{TEAL}"/>'
    body+=text(873,y+29,label,15,TEAL,600)
for y in [195,320,578]:body+=arrow(830,y,860,y,both=True)+arrow(1000,y,1040,y,both=True)
body+=arrow(354,205,430,195,'PCM / WS')
body+=arrow(354,377,430,320,'HTTP')
body+=arrow(630,235,630,275)
body+=arrow(630,365,630,405)
body+=arrow(630,495,630,535)
body+=arrow(830,450,1040,450,'SQLAlchemy',both=True)
body+=f'<path d="M430,570 L390,570 L390,405 L354,405" stroke="{TEAL}" stroke-width="2" fill="none" marker-end="url(#arrow)"/>'
body+=f'<path d="M430,601 L405,601 L405,588 L354,588" stroke="{TEAL}" stroke-width="2" fill="none" marker-end="url(#arrow)"/>'
body+=text(44,655,'LLM interprets and selects evidence; Python resolves identity, queries records and checks draft evidence and qualifiers before saving.',16,INK)
body+=text(44,680,'All cloud links pass through adapters for timeouts, retries and fallback. Keys stay server-side. Exact replies / pure thanks can stay local.',15,MUTED)
flows=[
 ('RETRIEVAL', '1 Voice: STT / typed text -> 2 HTTP command -> 3 retrieve plan -> 4 identity + ambiguity rules -> 5 latest-report SQL -> 6 report + source'),
 ('DICTATION TO DRAFT', '1 Transcript -> 2 LLM extraction -> 3 validate_findings (quotes, site, negation, uncertainty) -> 4 editable JSON -> 5 clinician review -> 6 versioned save'),
 ('CONTEXTUAL FOLLOW-UP', '1 Question -> 2 session patient / report scope -> 3 grounded LLM evidence -> 4 quote / version checks -> 5 answer + source excerpt -> optional TTS'),
]
for y,(title,flow) in zip([705,800,895],flows):
    body+=f'<rect x="44" y="{y}" width="1352" height="82" rx="8" fill="{WHITE}" stroke="{LINE}"/>'
    body+=text(60,y+27,title,16,TEAL,600)
    body+=text(60,y+58,flow,15,MUTED)
svg('system-architecture','VI-SCAN | Architecture and report-generation flows','Logical components above; numbered execution paths below. Synthetic-data proof of concept - no imaging diagnosis or clinical signing.',body)

body=''
steps=[('1. Understand the request',['Final transcript or typed command','Extract patient name + report modality']),('2. Resolve identity',['Zero matches: retain request for correction','Approximate or multiple: ask to confirm']),('3. Validate the selection',['Natural replies: explicit directory identity','Reject ambiguous names and stale context']),('4. Retrieve the correct report',['Patient scope + requested modality','Latest date selected deterministically']),('5. Save explicit context',['Selected patient + report ID/version','Show source, report date and modality']),('6. Answer a follow-up',['Named or pronoun context; source checks','Explicit all reports: separate cited summaries'])]
coords=[(44,160),(520,160),(996,160),(44,470),(520,470),(996,470)]
for (title,lines),(x,y) in zip(steps,coords):body+=box(x,y,400,150,title,lines,True)
body+=arrow(444,235,520,235)
body+=arrow(920,235,996,235)
body+=f'<path d="M1196,310 L1196,385 L244,385 L244,470" stroke="{TEAL}" stroke-width="2" fill="none" marker-end="url(#arrow)"/>'
body+=arrow(444,545,520,545)
body+=arrow(920,545,996,545)
body+=box(44,730,650,170,'Ambiguity is an application state',['Two Priyas never resolve by similarity score alone.','Suspend pronoun follow-ups during an unresolved switch.','No matching modality: clear active report and explain.'])
body+=box(746,730,650,170,'Evidence remains inspectable',['Report IDs/versions and quotes remain inspectable.','Collection failures are labeled; selection is unchanged.','History restores old results; new UUIDs create new turns.'])
svg('retrieval-workflow','Retrieval and contextual follow-up','Mandatory workflows A and C, plus report-aware questions.',body)

body=''
steps=[('1. Capture observations',['Audio or typed transcript','Partials display; finalized utterance commits']),('2. Extract a structured draft',['Groq GPT-OSS 120B + strict schema','Findings, anatomy, polarity, certainty']),('3. Validate evidence',['Source-local anatomy and polarity','Reject unsupported or conflicting content']),('4. Render an editable draft',['Readable text from validated fields','No invented tooth numbering or diagnosis']),('5. Clinician edits and reviews',['Keep source transcript and revisions','Export validates edits; final save is separate']),('6. Save explicitly as draft',['Require a selected synthetic patient','Clinician review flag remains true'])]
for (title,lines),(x,y) in zip(steps,coords):body+=box(x,y,400,150,title,lines,True)
body+=arrow(444,235,520,235)+arrow(920,235,996,235)
body+=f'<path d="M1196,310 L1196,385 L244,385 L244,470" stroke="{TEAL}" stroke-width="2" fill="none" marker-end="url(#arrow)"/>'
body+=arrow(444,545,520,545)+arrow(920,545,996,545)
body+=box(44,730,650,170,'Preserve clinical meaning',['Possible remains uncertain; no definite is not certain absence.','Retain negation and correction markers.','Unresolved site conflicts trigger clarification.'])
body+=box(746,730,650,170,'Provenance does not prove entailment',['Verbatim evidence is necessary, not sufficient.','Use conservative rules and dedicated semantic tests.','Never present a draft as a signed clinical report.'])
svg('dictation-workflow','Clinical dictation to reviewed draft','Mandatory workflow B. Human review remains explicit at every save.',body)

body=''
stages=[('Capture',['Browser microphone','PCM over WebSocket']),('Transcribe',['Google live STT','Partials to UI only']),('Commit',['Pause / timer / manual stop','HTTP command + UUID']),('Interpret + tools',['Groq LLM + rules','Authorized tool result']),('Respond',['Text + evidence first','Then Groq Orpheus'])]
for i,(title,lines) in enumerate(stages):
    x=44+i*276
    body+=box(x,170,250,155,title,lines,True)
    if i<4:body+=arrow(x+250,247,x+276,247)
body+=box(44,460,650,190,'STT failure before commit',['Keep a bounded in-memory utterance buffer.','Submit it once to Groq Whisper Large v3.','After commit: never replay the same tool action.','No silent substitution of fixture responses.'])
body+=box(746,460,650,190,'Speech playback and interruption',['Interrupt stops playback and invalidates stale audio.','Speak short approved response text only.','Groq -> Google -> disclosed browser voice or text.','Human microphone and audibility remain unverified.'])
body+=box(44,760,1352,150,'What the experiments actually measured',['Google live STT: first partial 0.76-1.27 s; final 0.37-0.46 s after last audio chunk.','Groq 120B extraction: median 0.95 s. Orpheus full audio: median 1.71 s.','These are different small-sample measurements, not an end-to-end latency promise.'])
svg('voice-workflow','Voice lifecycle and fallback','One logical utterance, one committed command. Text is available before speech playback.',body)

# Extract canonical Mermaid sources for editable diagrams in documentation tools.
source=(ROOT/'system-design.md').read_text(encoding='utf-8')
names=['system-architecture','retrieval','dictation','voice-sequence','voice-state','data-model']
blocks=re.findall(r'```mermaid\n(.*?)\n```',source,re.S)
for name,block in zip(names,blocks):(DIAGRAMS/f'{name}.mmd').write_text(block+'\n',encoding='utf-8')

# Render the diagram-first PDF and portable previews from the same SVG source.
import subprocess
subprocess.run(['node',str(ROOT/'render_design_artifacts.cjs')],check=True)
print('Updated four portable diagrams, six Mermaid sources and the diagram-first PDF.')
