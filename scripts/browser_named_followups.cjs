const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1512,height:1000}});const errors=[];let speechRequests=0;
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/sessions/*/speech',r=>{speechRequests++;return r.abort();});
  await page.goto('http://127.0.0.1:8000');await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
  async function send(text){
   await page.getByRole('textbox',{name:'Assistant request'}).fill(text);
   const response=page.waitForResponse(r=>r.url().endsWith('/commands'));
   await page.getByRole('button',{name:'Send request',exact:true}).click();
   const r=await response;if(!r.ok())throw Error('Command HTTP '+r.status());return r.json();
  }
  const suggested=await send("Hey, open the Rohit Desai's report.");
  if(!suggested.candidates?.some(p=>p.id==='PT-005')||suggested.patient)throw Error('Wrong confirmation');
  const opened=await send('Yes.');if(opened.report?.id!=='RPT-005-03')throw Error('Wrong report');
  const replies=[];
  for(const question of ["Okay, so can you tell me what are the findings in Rohan's report?","I asked what are the findings in Rohan Desai's report.","Show me the findings in Rohan's report."]){
   const result=await send(question);
   if(result.kind!=='answer'||!result.evidence?.length||result.evidence.some(e=>e.report_id!=='RPT-005-03'))throw Error('Named follow-up failed: '+JSON.stringify(result));
   if(result.session.context_version!==opened.session.context_version||result.trace.some(t=>t.tool==='get_latest_report'))throw Error('Question reopened report');
   replies.push({question,message:result.message,trace:result.trace,evidence:result.evidence});
  }
  const other=await send("What are the findings in Meera Iyer's report?");
  if(other.kind!=='clarification'||other.evidence.length||other.session.patient.id!=='PT-005')throw Error('Cross-patient identity guard failed');
  await page.reload();await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
  await page.locator('.message.user').filter({hasText:'I asked what are the findings'}).waitFor();
  await page.getByRole('heading',{name:'Rohan Desai',exact:true}).waitFor();
  if(errors.length||speechRequests)throw Error(JSON.stringify({errors,speechRequests}));
  await page.screenshot({path:'verification/named-followups-browser.png',fullPage:true});
  fs.writeFileSync('verification/named-followups-browser.json',JSON.stringify({passed:['Rohit Desai suggests Rohan with confirmation','Yes opens Rohan OPG','named first-name findings question answers current source','repeated full-name findings question answers without reopening','show findings remains a question','different patient question requires explicit source switch','history and selection survive refresh'],replies,speechRequests,pageErrors:errors,limitation:'Live text LLM with muted/blocked speech; no microphone or STT/TTS calls. This does not establish human speech recognition or universal conversational correctness.'},null,2));
  console.log('Named follow-up browser sequence passed; zero STT/TTS calls.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
