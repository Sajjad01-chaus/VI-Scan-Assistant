const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1512,height:950}});let speechRequests=0;const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/sessions/*/speech',r=>{speechRequests++;return r.abort();});
  await page.goto('http://127.0.0.1:8000');await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
  async function send(text){await page.getByRole('textbox',{name:'Assistant request'}).fill(text);const response=page.waitForResponse(r=>r.url().endsWith('/commands'));await page.getByRole('button',{name:'Send request',exact:true}).click();const r=await response;const data=await r.json();if(!r.ok()||['error','validation'].includes(data.kind))throw Error(JSON.stringify(data));return data;}
  await send('Open Priya Sharma report');
  const simple=await send('Thanks for this, but can you explain me the findings from this report in the simple words?');
  if(!simple.message.includes('wisdom tooth')||!simple.message.includes('lying sideways')||!simple.evidence.length)throw Error('Plain-language finding failed: '+JSON.stringify(simple));
  if(!simple.evidence.some(e=>/horizontally impacted/i.test(e.quote)))throw Error('Original evidence was replaced');
  await send('Open Arjun Mehta report');
  const technique=await send('Which imaging technique does his report describe?');
  if(!technique.message.includes('mock report describes a panoramic dental X-ray (OPG)')||!technique.evidence.some(e=>e.quote==='Synthetic panoramic dental radiograph text scenario.'))throw Error('Technique explanation failed: '+JSON.stringify(technique));
  if(errors.length||speechRequests)throw Error(JSON.stringify({errors,speechRequests}));
  await page.screenshot({path:'verification/plain-language-browser.png',fullPage:true});
  fs.writeFileSync('verification/plain-language-browser.json',JSON.stringify({passed:['user mixed thanks/simple-language request produces plain-language finding','original clinical quotations retained as evidence','technique described as mock OPG rather than implying completed imaging'],simple:{message:simple.message,evidence:simple.evidence},technique:{message:technique.message,evidence:technique.evidence},speechRequests,pageErrors:errors,limitation:'Live text LLM, speech muted/blocked, no microphone. Controlled renderer is bounded and does not cover every medical phrase.'},null,2));
  console.log('Live text-only plain-language and technique check passed; no STT/TTS calls.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
