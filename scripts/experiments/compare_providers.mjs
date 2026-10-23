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
const save=r => {results.push(r); fs.writeFileSync(path.join(output,'provider-comparison.json'),JSON.stringify({methodology:'Four Windows synthetic voice clips. Same input across providers. File STT measured from submission to full response; not comparable to streaming partial latency. TTS measured to first response byte and full audio, not playback. Small exploratory sample; no clinical or human voice validation.',results},null,2)); console.log(JSON.stringify(r));};
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
for(const c of cases){
 const audio=fs.readFileSync(path.join(output,`${c.id}.wav`));
 for(const model of ['whisper-large-v3','whisper-large-v3-turbo']){
  const form=new FormData();form.set('file',new Blob([audio],{type:'audio/wav'}),`${c.id}.wav`);form.set('model',model);form.set('language','en');form.set('response_format','json');form.set('temperature','0');
  const r=await request('groq','https://api.groq.com/openai/v1/audio/transcriptions',form,false);
  if(r.ok){const data=JSON.parse(r.bytes.toString());r.transcript=data.text;r.wer=wer(c.text,data.text);}delete r.bytes;save({task:'file_stt',provider:'groq',model,caseId:c.id,reference:c.text,...r});
 }
 const model='gemini-3.5-transcribe';
 const r=await request('google',`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`,{contents:[{parts:[{text:'Transcribe this audio verbatim. Return only the transcript.'},{inlineData:{mimeType:'audio/wav',data:audio.toString('base64')}}]}]});
 if(r.ok){const data=JSON.parse(r.bytes.toString());r.transcript=data.candidates?.[0]?.content?.parts?.map(p=>p.text||'').join('')||'';r.wer=r.transcript?wer(c.text,r.transcript):null;if(!r.transcript)r.scoringStatus='Unscored: response content was not parsed';fs.writeFileSync(path.join(output,`google-file-${c.id}-raw.json`),JSON.stringify(data,null,2));}delete r.bytes;save({task:'file_stt',provider:'google',model,caseId:c.id,reference:c.text,...r});
}
const speech='Your draft report is ready for clinician review.';
for(let trial=1;trial<=3;trial++){
 for(const provider of (trial%2?['groq','google']:['google','groq'])){
  const model=provider==='groq'?'canopylabs/orpheus-v1-english':'gemini-3.8-flash-lite-tts';
  const endpoint=provider==='groq'?'https://api.groq.com/openai/v1/audio/speech':`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
  const body=provider==='groq'?{model,input:speech,voice:'troy',response_format:'wav'}:{contents:[{parts:[{text:`Say clearly: ${speech}`}]}],generationConfig:{responseModalities:['AUDIO'],speechConfig:{voiceConfig:{prebuiltVoiceConfig:{voiceName:'Kore'}}}}};
  const r=await request(provider,endpoint,body);
  if(r.ok){let audio=r.bytes;if(provider==='google'){const data=JSON.parse(audio.toString());const part=data.candidates?.[0]?.content?.parts?.find(p=>p.inlineData);audio=part?Buffer.from(part.inlineData.data,'base64'):Buffer.alloc(0);}r.audioBytes=audio.length;r.audioFile=`${provider}-tts-trial-${trial}.wav`;fs.writeFileSync(path.join(output,r.audioFile),audio);}delete r.bytes;save({task:'tts',provider,model,trial,text:speech,...r});
 }
}
const schema={type:'object',properties:{findings:{type:'array',items:{type:'object',properties:{observation:{type:'string'},site:{type:'string'},certainty:{type:'string',enum:['asserted','uncertain','negated']},evidence:{type:'string'}},required:['observation','site','certainty','evidence'],additionalProperties:false}},requires_clinician_review:{type:'boolean'}},required:['findings','requires_clinician_review'],additionalProperties:false};
for(const model of ['openai/gpt-oss-120b','openai/gpt-oss-20b']){
 for(const c of cases.filter(c=>c.id!=='retrieval')){
  const r=await request('groq','https://api.groq.com/openai/v1/chat/completions',{model,temperature:0,max_completion_tokens:1800,messages:[{role:'system',content:'Extract clinical observations only from the supplied transcript. Preserve uncertainty and negation. Apply explicit corrections. Do not invent diagnoses, findings, or treatment. Evidence must be a verbatim excerpt. Always require clinician review.'},{role:'user',content:c.text}],response_format:{type:'json_schema',json_schema:{name:'clinical_draft',strict:true,schema}}});
  if(r.ok){const data=JSON.parse(r.bytes.toString());r.content=data.choices?.[0]?.message?.content;r.usage=data.usage;try{const parsed=JSON.parse(r.content);r.reviewRequired=parsed.requires_clinician_review===true;r.evidenceVerbatim=parsed.findings.every(f=>c.text.includes(f.evidence));}catch{r.jsonParseFailed=true;}}delete r.bytes;save({task:'clinical_extraction',provider:'groq',model,caseId:c.id,source:c.text,...r});
 }
}
console.log('Comparison complete; inspect outputs before selecting models.');
