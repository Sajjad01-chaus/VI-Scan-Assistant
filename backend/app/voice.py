"""A manual-stop streaming transcription session. Commands are committed by HTTP once."""
import asyncio
import base64
import json
import math
import struct
import websockets
from fastapi import WebSocket, WebSocketDisconnect
from .providers import ProviderError

async def relay_voice(browser: WebSocket, ai):
    buffer=bytearray();finals=[];partial='';provider='google';remote=None
    received=asyncio.Event();failed=False
    async def read_remote():
        nonlocal partial,failed
        try:
            async for raw in remote:
                data=json.loads(raw)
                if data.get('error'):failed=True;received.set();return
                content=data.get('serverContent',{})
                if content.get('interimInputTranscription'):
                    partial=content['interimInputTranscription']['text']
                    await browser.send_json({'type':'transcript.partial','text':' '.join(finals+[partial])})
                if content.get('inputTranscription'):
                    text=content['inputTranscription']['text'].strip()
                    if text:finals.append(text)
                    partial='';received.set()
                    await browser.send_json({'type':'transcript.segment','text':' '.join(finals)})
        except (websockets.ConnectionClosed, OSError):failed=True;received.set()

    task=None
    try:
        if ai.config.mode!='live':
            await browser.send_json({'type':'error','message':'Live microphone transcription requires AI_MODE=live. Use sample transcripts in fixture mode.'});return
        try:
            remote=await websockets.connect('wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent',additional_headers={'x-goog-api-key':ai.config.google_key},open_timeout=8,max_size=2**20)
            await remote.send(json.dumps({'setup':{'model':'models/'+ai.config.google_stt,'generationConfig':{'responseModalities':['TEXT']},'inputAudioTranscription':{}}}))
            ack=json.loads(await asyncio.wait_for(remote.recv(),8))
            if 'setupComplete' not in ack:raise ValueError('Setup refused')
            task=asyncio.create_task(read_remote())
        except (OSError,ValueError,TimeoutError,websockets.WebSocketException):
            provider='groq-fallback';failed=True
            if remote:await remote.close()
            remote=None
        await browser.send_json({'type':'voice.ready','provider':provider,'max_seconds':20})
        while True:
            message=await asyncio.wait_for(browser.receive(),30)
            if message['type']=='websocket.disconnect':return
            if message.get('bytes'):
                chunk=message['bytes']
                if len(chunk)%2 or len(chunk)>32000:raise ValueError('Invalid audio frame.')
                if len(buffer)+len(chunk)>640000:raise ValueError('Audio limit is 20 seconds. Stop and submit a shorter utterance.')
                buffer.extend(chunk)
                if remote and not failed:
                    try:await remote.send(json.dumps({'realtimeInput':{'audio':{'mimeType':'audio/pcm;rate=16000','data':base64.b64encode(chunk).decode()}}}))
                    except websockets.ConnectionClosed:failed=True
            elif message.get('text'):
                control=json.loads(message['text'])
                if control.get('type')=='cancel':return
                if control.get('type')=='stop':break
        # Silence is never routed into a clinical action.
        samples=struct.unpack('<'+'h'*(len(buffer)//2),buffer) if buffer else ()
        rms=math.sqrt(sum(s*s for s in samples)/len(samples)) if samples else 0
        if len(buffer)<3200 or rms<80:
            await browser.send_json({'type':'error','message':'No clear speech detected. Try again or type a transcript.'});return
        if remote and not failed:
            received.clear()
            await remote.send(json.dumps({'realtimeInput':{'audioStreamEnd':True}}))
            if not finals or partial:
                try:await asyncio.wait_for(received.wait(),3)
                except TimeoutError:pass
            # Allow closely spaced final segments to arrive before freezing the utterance.
            await asyncio.sleep(.3)
        text=' '.join(finals).strip()
        if failed or not text:
            provider='groq-fallback'
            text=await ai.file_stt(bytes(buffer))
        await browser.send_json({'type':'transcript.final','text':text,'provider':provider})
    except (WebSocketDisconnect,RuntimeError):pass
    except ProviderError as e:
        await browser.send_json({'type':'error','message':e.message,'code':e.code})
    except (ValueError,TimeoutError):
        await browser.send_json({'type':'error','message':'Voice session ended or audio was invalid. Use a short utterance or typed input.'})
    finally:
        if task:
            task.cancel()
            try:await task
            except (asyncio.CancelledError,RuntimeError,WebSocketDisconnect):pass
        if remote:await remote.close()
        buffer.clear()
