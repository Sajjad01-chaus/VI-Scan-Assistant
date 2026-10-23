// Small synthetic benchmark; results do not establish clinical accuracy.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const output = path.join(root, 'verification');
const keys = Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').replace(/^\uFEFF/,'').split(/\r?\n/).filter(l => l.includes('=') && !l.trim().startsWith('#')).map(l => { const i=l.indexOf('='); return [l.slice(0,i).trim(), l.slice(i+1).trim().replace(/^['"]|['"]$/g,'')]; }));
if (!keys.GROQ_API_KEY || !keys.GOOGLE_API_KEY) {console.log('Both GOOGLE_API_KEY and GROQ_API_KEY must be populated.'); process.exit(1);}
const cases=JSON.parse(fs.readFileSync(path.join(output,'benchmark-cases.json'),'utf8'));
const results=[];
const redact=s => Object.values(keys).filter(Boolean).reduce((s,k) => s.split(k).join('[REDACTED]'),String(s));
const save=r => {results.push(r); fs.writeFileSync(path.join(output,'google-tts-exact-text.json'),JSON.stringify({methodology:'Three TTS requests per provider with alternating order and identical short response. Times include network and complete response transfer, not time to playable streaming audio. Voice quality not scored.',results},null,2)); console.log(JSON.stringify(r));};
const normalize=s => s.toLowerCase().replace(/[^a-z0-9\s]/g,'').trim().split(/\s+/).filter(Boolean);
function wer(reference,hypothesis) {
 const a=normalize(reference),b=normalize(hypothesis); let prev=Array.from({length:b.length+1},(_,i)=>i);
 for(let i=1;i<=a.length;i++){const row=[i];for(let j=1;j<=b.length;j++)row[j]=Math.min(row[j-1]+1,prev[j]+1,prev[j-1]+(a[i-1]===b[j-1]?0:1));prev=row;}
 return prev[b.length]/Math.max(a.length,1);
}
async function request(provider,endpoint,body,json=true){
 const start=performance.now();
 try {
  const headers=provider==='groq'?{Authorization:`Bearer ${keys.GROQ_API_KEY}`}:{'x-goog-api-key':keys.GOOGLE_API_KEY};
  if(json)headers['Content-Type']='application/json';
  const response=await fetch(endpoint,{method:'POST',headers,body:json?JSON.stringify(body):body,signal:AbortSignal.timeout(45000)});
  const headersMs=Math.round(performance.now()-start);
  const bytes=Buffer.from(await response.arrayBuffer());
  const elapsedMs=Math.round(performance.now()-start);
  if(!response.ok)return {ok:false,http:response.status,headersMs,elapsedMs,error:redact(bytes.toString()).slice(0,1600)};
  return {ok:true,http:response.status,headersMs,elapsedMs,bytes};
 }catch(e){return {ok:false,error:redact(e.message),elapsedMs:Math.round(performance.now()-start)};}
}
const speech='Your draft report is ready for clinician review.';
for(let trial=1;trial<=3;trial++){
 for(const provider of ['google']){
  const model=provider==='groq'?'canopylabs/orpheus-v1-english':'gemini-3.8-flash-lite-tts';
  const endpoint=provider==='groq'?'https://api.groq.com/openai/v1/audio/speech':`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
  const body=provider==='groq'?{model,input:speech,voice:'troy',response_format:'wav'}:{contents:[{parts:[{text:speech}]}],generationConfig:{responseModalities:['AUDIO'],speechConfig:{voiceConfig:{prebuiltVoiceConfig:{voiceName:'Kore'}}}}};
  const r=await request(provider,endpoint,body);
  if(r.ok){let audio=r.bytes;if(provider==='google'){const data=JSON.parse(audio.toString());const part=data.candidates?.[0]?.content?.parts?.find(p=>p.inlineData);audio=part?Buffer.from(part.inlineData.data,'base64'):Buffer.alloc(0);}r.audioBytes=audio.length;r.audioFile=`${provider}-tts-exact-trial-${trial}.wav`;fs.writeFileSync(path.join(output,r.audioFile),audio);}delete r.bytes;save({task:'tts',provider,model,trial,text:speech,...r});
 }
}
