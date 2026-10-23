import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..'), out=path.join(root,'verification');
const key=fs.readFileSync(path.join(root,'.env'),'utf8').replace(/^\uFEFF/,'').split(/\r?\n/).find(l=>l.startsWith('GOOGLE_API_KEY=')).slice('GOOGLE_API_KEY='.length).trim().replace(/^['"]|['"]$/g,'');
const cases=JSON.parse(fs.readFileSync(path.join(out,'benchmark-cases.json'),'utf8'));
const results=[];
for(const c of cases){
 const record={caseId:c.id,reference:c.text,model:'gemini-3.5-transcribe-live',partials:[],finals:[]};
 const start=performance.now();let sendStart,lastAudio;
 await new Promise(resolve=>{
  let done=false;
  const ws=new WebSocket(`wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=${encodeURIComponent(key)}`);
  const timer=setTimeout(()=>{record.timeout=true;finish();},30000);
  function finish(){if(done)return;done=true;clearTimeout(timer);record.totalSessionMs=Math.round(performance.now()-start);ws.close();resolve();}
  ws.addEventListener('open',()=>ws.send(JSON.stringify({setup:{model:'models/gemini-3.5-transcribe-live',generationConfig:{responseModalities:['TEXT']},inputAudioTranscription:{}}})));
  ws.addEventListener('message',async e=>{
   const data=JSON.parse(typeof e.data==='string'?e.data:await e.data.text());
   if(data.setupComplete){
    record.setupMs=Math.round(performance.now()-start);sendStart=performance.now();
    const wav=fs.readFileSync(path.join(out,`${c.id}.wav`)), idx=wav.indexOf(Buffer.from('data'),12), pcm=wav.subarray(idx+8,idx+8+wav.readUInt32LE(idx+4));
    record.audioDurationMs=pcm.length/32;
    for(let i=0;i<pcm.length&&!done;i+=3200){ws.send(JSON.stringify({realtimeInput:{audio:{mimeType:'audio/pcm;rate=16000',data:pcm.subarray(i,i+3200).toString('base64')}}}));await new Promise(r=>setTimeout(r,100));}
    lastAudio=performance.now();record.audioSentMs=Math.round(lastAudio-sendStart);
    if(!done)ws.send(JSON.stringify({realtimeInput:{audioStreamEnd:true}}));
   }
   const content=data.serverContent;
   if(content?.interimInputTranscription){if(record.firstPartialMs===undefined)record.firstPartialMs=Math.round(performance.now()-sendStart);record.partials.push(content.interimInputTranscription.text);}
   if(content?.inputTranscription){record.finals.push(content.inputTranscription.text);record.finalFromAudioStartMs=Math.round(performance.now()-sendStart);if(lastAudio)record.finalAfterSendMs=Math.round(performance.now()-lastAudio);}
   if(data.error){record.error=JSON.stringify(data.error).split(key).join('[REDACTED]');finish();}
   // Wait briefly after final to collect any additional segment finals.
   if(content?.inputTranscription){setTimeout(()=>{if(lastAudio)finish();},1000);}
  });
  ws.addEventListener('error',()=>{record.error='WebSocket error';finish();});
  ws.addEventListener('close',e=>{record.closeCode=e.code;record.closeReason=e.reason.split(key).join('[REDACTED]');finish();});
 });
 results.push(record);fs.writeFileSync(path.join(out,'google-live-comparison.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(record));
}
