import base64
import json
import urllib.request
import urllib.error
from verify_google import read_key, ROOT

key=read_key()
audio=(ROOT/'verification'/'retrieval.wav').read_bytes()
body={'contents':[{'parts':[{'text':'Transcribe this audio verbatim. Return only the transcript.'},{'inlineData':{'mimeType':'audio/wav','data':base64.b64encode(audio).decode()}}]}]}
req=urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-transcribe:generateContent',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','x-goog-api-key':key})
try:
 with urllib.request.urlopen(req,timeout=40) as response: result=json.load(response)
 (ROOT/'verification'/'google-file-transcribe-raw.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result).replace(key,'[REDACTED]')[:7000])
except urllib.error.HTTPError as error:
 print('HTTP',error.code,error.read().decode().replace(key,'[REDACTED]')[:1000])
