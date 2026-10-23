const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true,args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
 try {
  const page=await browser.newPage({viewport:{width:1512,height:1000}});
  const errors=[];let speechRequests=0,captures=0;
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/sessions/*/speech',route=>{speechRequests++;return route.abort();});
  const transcripts=['Hey, can you open Mira Yash report?','Thank you.','Meera Iyer'];
  await page.routeWebSocket('**/api/sessions/*/voice',ws=>{
   const transcript=transcripts[captures++];let sent=false;
   ws.onMessage(()=>{if(!sent){sent=true;ws.send(JSON.stringify({type:'transcript.final',text:transcript,provider:'controlled-test-transcript'}));}});
   ws.send(JSON.stringify({type:'voice.ready'}));
  });
  await page.goto('http://127.0.0.1:8000');
  const mute=async()=>{await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();};
  await mute();
  const command=()=>page.waitForResponse(r=>r.url().endsWith('/commands')).then(async r=>{if(!r.ok())throw Error('Command HTTP '+r.status()+': '+await r.text());return r;});
  async function speak(){const response=command();await page.getByRole('button',{name:'Start microphone',exact:true}).click();return (await response).json();}
  async function type(text){await page.getByRole('textbox',{name:'Assistant request'}).fill(text);const response=command();await page.getByRole('button',{name:'Send request',exact:true}).click();return (await response).json();}
  const first=await speak();
  if(first.patient||!first.candidates?.some(p=>p.id==='PT-006'))throw Error('Misheard name did not offer Meera for confirmation');
  const thanks=await speak();
  if(thanks.kind!=='acknowledgement')throw Error('Acknowledgement lost pending conversation');
  const corrected=await speak();
  if(corrected.report?.id!=='RPT-006-03'||corrected.report.modality!=='IOPA')throw Error('Corrected full name did not complete original request');
  await page.getByRole('heading',{name:'Meera Iyer',exact:true}).waitFor();
  const newSession=page.waitForResponse(r=>r.url().endsWith('/api/sessions')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'New session',exact:true}).click();await newSession;await mute();
  const missing=await type("Open Unknown Person's report");
  if(missing.patient||missing.candidates?.length)throw Error('Unknown identity was selected');
  await page.getByRole('heading',{name:'What is the patient’s correct name?',exact:true}).waitFor();
  const session=await page.evaluate(()=>sessionStorage.getItem('viscan-session'));
  await page.reload();await mute();
  await page.getByRole('heading',{name:'What is the patient’s correct name?',exact:true}).waitFor();
  if(await page.evaluate(()=>sessionStorage.getItem('viscan-session'))!==session)throw Error('Refresh lost session');
  const recovered=await type('Meera Iyer');
  if(recovered.report?.id!=='RPT-006-03')throw Error('Empty-candidate correction failed');
  await page.getByRole('heading',{name:'Meera Iyer',exact:true}).waitFor();
  await page.reload();await mute();
  await page.getByRole('heading',{name:'Meera Iyer',exact:true}).waitFor();
  await page.locator('.message.user').filter({hasText:'Unknown Person'}).waitFor();
  await page.locator('.message.user').filter({hasText:'Meera Iyer'}).waitFor();
  if(errors.length||speechRequests||captures!==3)throw Error(JSON.stringify({errors,speechRequests,captures}));
  await page.screenshot({path:'verification/name-recovery-audit.png',fullPage:true});
  fs.writeFileSync('verification/name-recovery-audit.json',JSON.stringify({passed:['misheard Mira Yash offers Meera Iyer without selecting','Thank you preserves pending request','bare corrected full name opens original requested report','zero matches asks for corrected name','pending request survives refresh','bare full name recovers zero-match request','chat and selected report survive refresh'],captures,speechRequests,pageErrors:errors,limitation:'Controlled final STT transcripts and fake microphone, with no upstream STT connection. Speech is muted and blocked. LLM routing is live; human transcription accuracy and actual audio output are not tested.'},null,2));
  console.log('Name recovery browser audit passed; zero STT/TTS provider calls.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
