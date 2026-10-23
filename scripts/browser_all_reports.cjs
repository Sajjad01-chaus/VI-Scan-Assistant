const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1512,height:1000}});
  const errors=[];let speechRequests=0;
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/sessions/*/speech',r=>{speechRequests++;return r.abort();});
  await page.goto('http://127.0.0.1:8000');
  await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
  async function send(text){
   await page.getByRole('textbox',{name:'Assistant request'}).fill(text);
   const response=page.waitForResponse(r=>r.url().endsWith('/commands'));
   await page.getByRole('button',{name:'Send request',exact:true}).click();
   const r=await response;if(!r.ok())throw Error('Command HTTP '+r.status());
   const result=await r.json();if(['error','validation'].includes(result.kind))throw Error(JSON.stringify(result));return result;
  }
  await page.getByRole('button',{name:'Open Priya’s latest OPG report',exact:true}).click();
  await page.getByRole('region',{name:'Confirm patient identity'}).waitFor();
  await page.locator('.candidate-list button').filter({hasText:'Priya Sharma'}).click();
  await page.getByRole('heading',{name:'Priya Sharma',exact:true}).waitFor();
  const cbct=await send("Hey, open Priya Sharma's latest CBCT report.");
  if(cbct.report?.id!=='RPT-001-02')throw Error('CBCT was not selected');
  const all=await send('Summarize her all reports.');
  const expected=['RPT-001-03','RPT-001-02','RPT-001-01'];
  if(!all.complete||JSON.stringify(all.report_ids)!==JSON.stringify(expected))throw Error('All-report scope failed: '+JSON.stringify(all));
  if(expected.some(id=>!all.evidence.some(e=>e.report_id===id)))throw Error('Missing report citations');
  if(all.session.report.id!=='RPT-001-02')throw Error('Summary changed selection');
  const message=page.locator('.message.assistant').filter({hasText:'Summary of all available reports (3)'});
  await message.waitFor();
  await message.locator('.citations button').filter({hasText:'RPT-001-01'}).first().click();
  await page.getByRole('region',{name:'Cited source evidence'}).waitFor();
  if(!(await page.locator('.active-context').innerText()).includes('RPT-001-02'))throw Error('Citation switched active report');
  await page.screenshot({path:'verification/all-reports-browser.png',fullPage:true});
  await page.reload();await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
  await page.locator('.message.assistant').filter({hasText:'Summary of all available reports (3)'}).waitFor();
  const single=await send('Summarize her report');
  if(single.evidence.some(e=>e.report_id!=='RPT-001-02'))throw Error('Single report summary leaked scope');
  if(errors.length||speechRequests)throw Error(JSON.stringify({errors,speechRequests}));
  fs.writeFileSync('verification/all-reports-browser.json',JSON.stringify({passed:['original Priya ambiguity and selection','CBCT switch','exact all-reports request covers all three reports','every report has cited evidence','older citation preview preserves selected CBCT','multi-report chat survives refresh','subsequent singular summary stays on selected CBCT'],reportIds:all.report_ids,response:all.message,speechRequests,pageErrors:errors,limitation:'Live text LLM with speech muted and blocked; no microphone or STT/TTS calls. Spoken overview transport is separately verified with a local stub, not audible cloud output.'},null,2));
  console.log('All-reports browser audit passed; zero STT/TTS calls.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
