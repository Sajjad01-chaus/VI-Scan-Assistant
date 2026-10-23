import asyncio
import hashlib
import json
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Cookie, HTTPException, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import select
from .config import ROOT, settings
from . import db as store
from .providers import AI, ProviderError
from .service import Service, patient_dict, report_dict
from .schemas import Command, Selection, DraftEdit, Version, SpeechRequest
from .voice import relay_voice

ai=AI();service=Service(ai)
build_files=[ROOT/'backend/app'/name for name in ['main.py','service.py','providers.py','answers.py','schemas.py','voice.py']]+[ROOT/'frontend/dist/index.html']
BUILD_ID=hashlib.sha256(b''.join(p.read_bytes() for p in build_files if p.exists())).hexdigest()[:12]

@asynccontextmanager
async def lifespan(app):
    # Schema creation is explicit: run `python -m backend.bootstrap` before starting.
    yield

app=FastAPI(title='VI-SCAN synthetic dental assistant',version='0.1.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=settings.origins,allow_credentials=True,allow_methods=['GET','POST','PATCH'],allow_headers=['Content-Type'])

@app.middleware('http')
async def browser_boundary(request:Request, call_next):
    if request.method in ('POST','PATCH','DELETE'):
        origin=request.headers.get('origin')
        if origin and origin not in settings.origins:return Response('Origin not allowed',status_code=403)
        try:
            if int(request.headers.get('content-length','0'))>65536:return Response('Request too large',status_code=413)
        except ValueError:return Response('Invalid content length',status_code=400)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['X-App-Build']=BUILD_ID
    if request.url.path.startswith('/api/'):response.headers['Cache-Control']='no-store'
    elif request.url.path in {'/','/pcm-worklet.js'}:response.headers['Cache-Control']='no-cache, must-revalidate'
    return response

@app.get('/api/health')
def health():
    try:
        with store.Session() as db:db.execute(select(store.Patient.id).limit(1))
        return {'status':'ok','synthetic_only':True}
    except Exception:raise HTTPException(503,'Database not initialized. Run python -m backend.bootstrap.') from None

@app.get('/api/config')
def config():
    return {'mode':settings.mode,'build_id':BUILD_ID,'synthetic_only':True,'live_configured':bool(settings.google_key and settings.groq_key),'models':{'llm':settings.llm_model,'stt':settings.google_stt,'tts':settings.groq_tts},'voice_max_seconds':20,'authorization':'Local demo cookie ownership, not production authentication'}

@app.post('/api/sessions')
def create_session(response:Response, viscan_owner:str|None=Cookie(default=None)):
    owner=viscan_owner or secrets.token_urlsafe(32)
    response.set_cookie('viscan_owner',owner,httponly=True,samesite='strict',secure=settings.cookie_secure,max_age=86400)
    return service.new_session(owner)

@app.get('/api/sessions/{session_id}')
def session(session_id:str,viscan_owner:str|None=Cookie(default=None)):
    return service.snapshot(session_id,viscan_owner)

@app.get('/api/sessions/{session_id}/history')
def history(session_id:str,viscan_owner:str|None=Cookie(default=None)):
    return service.history(session_id,viscan_owner)

@app.get('/api/patients')
def patients(viscan_owner:str|None=Cookie(default=None)):
    if not viscan_owner:raise HTTPException(401,'Create a demo session first.')
    with store.Session() as db:return [patient_dict(p) for p in db.scalars(select(store.Patient).order_by(store.Patient.name))]

@app.post('/api/sessions/{session_id}/commands')
async def commands(session_id:str,command:Command,viscan_owner:str|None=Cookie(default=None)):
    try:return await asyncio.wait_for(service.command(session_id,viscan_owner,command),55)
    except TimeoutError:raise HTTPException(504,'Turn deadline exceeded. Refresh state before retrying with a new utterance ID.') from None

@app.post('/api/sessions/{session_id}/selection')
async def selection(session_id:str,body:Selection,viscan_owner:str|None=Cookie(default=None)):
    return await service.select_patient(session_id,viscan_owner,body)

@app.get('/api/reports/{report_id}')
def report(report_id:str,session_id:str,viscan_owner:str|None=Cookie(default=None)):
    s=service.owned(session_id,viscan_owner)
    if s.pending_json or s.selected_report_id!=report_id:raise HTTPException(403,'Open this report in the session before viewing it.')
    with store.Session() as db:return report_dict(db.get(store.Report,report_id))

@app.get('/api/drafts/{draft_id}')
def draft(draft_id:str,viscan_owner:str|None=Cookie(default=None)):
    return service.get_draft(draft_id,viscan_owner)

@app.patch('/api/drafts/{draft_id}')
async def edit(draft_id:str,body:DraftEdit,viscan_owner:str|None=Cookie(default=None)):
    return await service.edit_draft(draft_id,viscan_owner,body)

@app.post('/api/drafts/{draft_id}/save')
async def save(draft_id:str,body:Version,viscan_owner:str|None=Cookie(default=None)):
    return await service.save_draft(draft_id,viscan_owner,body.version)

@app.post('/api/sessions/{session_id}/speech')
async def speech(session_id:str,body:SpeechRequest,viscan_owner:str|None=Cookie(default=None)):
    service.owned(session_id,viscan_owner)
    with store.Session() as db:
        turn=db.get(store.Turn,body.turn_id)
        if not turn or turn.session_id!=session_id or not turn.response_json:raise HTTPException(404,'Response not found.')
        result=json.loads(turn.response_json)
        text=result.get('speech_text') or result['message']
    try:
        data,mime,provider=await ai.speak(text)
        return Response(content=data,media_type=mime,headers={'X-Speech-Provider':provider})
    except ProviderError as e:raise HTTPException(503,e.message) from None

@app.websocket('/api/sessions/{session_id}/voice')
async def voice(websocket:WebSocket,session_id:str):
    if websocket.headers.get('origin') not in settings.origins:
        await websocket.close(code=1008);return
    try:service.owned(session_id,websocket.cookies.get('viscan_owner'))
    except HTTPException:await websocket.close(code=1008);return
    await websocket.accept()
    await relay_voice(websocket,ai)
    try:await websocket.close()
    except RuntimeError:pass

dist=ROOT/'frontend'/'dist'
if dist.exists():
    app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
    @app.get('/pcm-worklet.js')
    def worklet():return FileResponse(dist/'pcm-worklet.js',media_type='application/javascript')
    @app.get('/favicon.svg')
    def favicon():return FileResponse(dist/'favicon.svg',media_type='image/svg+xml')
    @app.get('/')
    def index():return FileResponse(dist/'index.html')
