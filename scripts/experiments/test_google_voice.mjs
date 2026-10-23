import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const env = fs.readFileSync(path.join(root, '.env'), 'utf8').replace(/^\uFEFF/, '');
const key = env.split(/\r?\n/).find(l => l.trim().startsWith('GOOGLE_API_KEY='))?.split('=').slice(1).join('=').trim().replace(/^['"]|['"]$/g, '');
if (!key) throw new Error('Missing Google key');
const output = path.join(root, 'verification');
const results = [];
const clean = text => String(text).split(key).join('[REDACTED]');
async function generate(model, body, label) {
  const start = performance.now();
  try {
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
      method: 'POST', headers: {'x-goog-api-key': key, 'Content-Type': 'application/json'}, body: JSON.stringify(body), signal: AbortSignal.timeout(40000)
    });
    const data = await response.json();
    const record = {label, model, http: response.status, elapsedMs: Math.round(performance.now()-start)};
    if (!response.ok) record.error = clean(data.error?.message || JSON.stringify(data));
    else {
      const parts = data.candidates?.[0]?.content?.parts || [];
      record.text = parts.filter(p => p.text).map(p => p.text).join('');
      const audio = parts.find(p => p.inlineData?.data);
      if (audio) {
        const bytes = Buffer.from(audio.inlineData.data, 'base64');
        const extension = audio.inlineData.mimeType?.includes('wav') ? 'wav' : 'pcm';
        fs.writeFileSync(path.join(output, `${model}.${extension}`), bytes);
        record.audioBytes = bytes.length;
        record.mimeType = audio.inlineData.mimeType;
      }
    }
    results.push(record); console.log(JSON.stringify(record));
  } catch (e) { const record = {label, model, error: clean(e.message)}; results.push(record); console.log(JSON.stringify(record)); }
}
await generate('gemini-3.8-flash-lite-tts', {
  contents: [{parts: [{text: 'Say clearly: Your draft report is ready for clinician review.'}]}],
  generationConfig: {responseModalities: ['AUDIO'], speechConfig: {voiceConfig: {prebuiltVoiceConfig: {voiceName: 'Kore'}}}}
}, 'TTS');
await generate('gemini-2.5-flash-preview-tts', {
  contents: [{parts: [{text: 'Say clearly: Your draft report is ready for clinician review.'}]}],
  generationConfig: {responseModalities: ['AUDIO'], speechConfig: {voiceConfig: {prebuiltVoiceConfig: {voiceName: 'Kore'}}}}
}, 'TTS established model');
await generate('gemini-3.5-transcribe', {
  contents: [{parts: [{text: 'Transcribe this audio exactly.'}, {inlineData: {mimeType: 'audio/wav', data: fs.readFileSync(path.join(output, 'synthetic-dental.wav')).toString('base64')}}]}]
}, 'File transcription');
await new Promise(resolve => {
  const start = performance.now();
  const ws = new WebSocket(`wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=${encodeURIComponent(key)}`);
  let finished = false;
  const record = {label: 'Live STT', model: 'gemini-3.5-transcribe-live', events: []};
  function finish() {
    if (finished) return;
    finished = true; clearTimeout(timer); record.elapsedMs = Math.round(performance.now()-start);
    results.push(record); console.log(JSON.stringify(record)); ws.close(); resolve();
  }
  const timer = setTimeout(() => {record.timeout = true; finish();}, 20000);
  ws.addEventListener('open', () => ws.send(JSON.stringify({setup: {model: 'models/gemini-3.5-transcribe-live', generationConfig: {responseModalities: ['TEXT']}, inputAudioTranscription: {}}})));
  ws.addEventListener('message', async event => {
    const data = JSON.parse(typeof event.data === 'string' ? event.data : await event.data.text());
    record.events.push(data);
    if (data.setupComplete) {
      record.setupSucceeded = true;
      const wav = fs.readFileSync(path.join(output, 'synthetic-dental.wav'));
      const idx = wav.indexOf(Buffer.from('data'), 12);
      const pcm = wav.subarray(idx+8, idx+8+wav.readUInt32LE(idx+4));
      for (let i=0; i<pcm.length && !finished; i+=3200) {
        ws.send(JSON.stringify({realtimeInput: {audio: {mimeType:'audio/pcm;rate=16000', data:pcm.subarray(i,i+3200).toString('base64')}}}));
        await new Promise(r => setTimeout(r,100));
      }
      if (!finished) ws.send(JSON.stringify({realtimeInput:{audioStreamEnd:true}}));
    }
    if (data.serverContent?.inputTranscription || data.error) finish();
  });
  ws.addEventListener('error', () => {record.error = 'WebSocket connection error'; finish();});
  ws.addEventListener('close', event => {record.closeCode = event.code; record.closeReason = clean(event.reason); finish();});
});
fs.writeFileSync(path.join(output, 'google-voice-results.json'), JSON.stringify(results, null, 2));
