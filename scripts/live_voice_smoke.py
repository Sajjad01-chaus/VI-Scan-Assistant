"""Exercise the actual FastAPI voice WebSocket with synthetic PCM input."""
import os
os.environ['AI_MODE']='live'
import asyncio
import json
import time
import wave
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app,ai

root=Path(__file__).resolve().parents[1]
with wave.open(str(root/'verification'/'negation.wav'),'rb') as w:pcm=w.readframes(w.getnframes())
events=[]
with TestClient(app) as client:
    session=client.post('/api/sessions',json={}).json()
    with client.websocket_connect('/api/sessions/'+session['id']+'/voice',headers={'origin':'http://127.0.0.1:8000'}) as ws:
        ready=ws.receive_json();print('Voice provider:',ready.get('provider'));events.append(ready)
        assert ready['type']=='voice.ready',ready
        start=time.perf_counter()
        for i in range(0,len(pcm),3200):ws.send_bytes(pcm[i:i+3200]);time.sleep(.1)
        ws.send_json({'type':'stop'})
        while True:
            event=ws.receive_json();events.append(event)
            if event['type'] in ('transcript.final','error'):break
        assert event['type']=='transcript.final',event
        assert 'No evidence of a fracture' in event['text'],event
        print('Final transcript:',event['text'])
        print('Session duration ms:',round((time.perf_counter()-start)*1000))
        assert ready['provider']=='google','Primary streaming connection fell back unexpectedly.'
fallback=asyncio.run(ai.file_stt(pcm))
print('File-STT adapter:',fallback)
assert 'fracture' in fallback.lower()
(root/'verification'/'app-live-voice.json').write_text(json.dumps({'events':events,'file_fallback_transcript':fallback},indent=2),encoding='utf-8')
print('Live voice adapter smoke passed.')
