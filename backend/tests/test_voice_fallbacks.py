import asyncio
import base64
import copy
import io
import struct
import wave
from backend.app import providers
from backend.app.config import settings
from backend.app.providers import AI,ProviderError
from backend.tests.test_workflows import client,new
import backend.app.main as main
import backend.app.voice as voice_module

def test_streaming_outage_uses_file_stt_once(client,monkeypatch):
    main.ai.config.mode='live';calls=[]
    async def offline(*args,**kwargs):raise OSError('simulated outage')
    async def transcribe(pcm):calls.append(len(pcm));return 'Lower right third molar is horizontally impacted.'
    monkeypatch.setattr(voice_module.websockets,'connect',offline)
    monkeypatch.setattr(main.ai,'file_stt',transcribe)
    s=new(client)
    with client.websocket_connect('/api/sessions/'+s['id']+'/voice',headers={'origin':'http://127.0.0.1:8000'}) as ws:
        ready=ws.receive_json();assert ready['provider']=='groq-fallback'
        ws.send_bytes(struct.pack('<1600h',*([1000]*1600)));ws.send_json({'type':'stop'})
        final=ws.receive_json();assert final['type']=='transcript.final' and final['provider']=='groq-fallback'
    assert calls==[3200]
    assert client.get('/api/sessions/'+s['id']+'/history').json()['messages']==[]

def test_silence_never_calls_file_stt(client,monkeypatch):
    main.ai.config.mode='live'
    async def offline(*args,**kwargs):raise OSError('simulated outage')
    async def forbidden(_):raise AssertionError('Silence must not be transcribed')
    monkeypatch.setattr(voice_module.websockets,'connect',offline)
    monkeypatch.setattr(main.ai,'file_stt',forbidden)
    s=new(client)
    with client.websocket_connect('/api/sessions/'+s['id']+'/voice',headers={'origin':'http://127.0.0.1:8000'}) as ws:
        ws.receive_json();ws.send_bytes(bytes(6400));ws.send_json({'type':'stop'})
        assert ws.receive_json()['type']=='error'

def test_tts_outage_returns_google_audio(client,monkeypatch):
    cfg=copy.copy(settings);cfg.mode='live';calls=[]
    audio=io.BytesIO()
    with wave.open(audio,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(bytes(4800))
    class Response:
        def json(self):return {'candidates':[{'content':{'parts':[{'inlineData':{'mimeType':'audio/wav','data':base64.b64encode(audio.getvalue()).decode()}}]}}]}
    async def fake(url,*args,**kwargs):
        calls.append(url)
        if 'groq.com' in url:raise ProviderError()
        return Response()
    monkeypatch.setattr(providers,'post',fake)
    data,mime,provider=asyncio.run(AI(cfg).speak('Draft ready for review.'))
    assert provider=='google-fallback' and mime=='audio/wav' and data.startswith(b'RIFF')
    assert len(calls)==2
