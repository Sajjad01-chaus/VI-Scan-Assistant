const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1512,height:1000}});const errors=[];let speechRequests=0;
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/sessions/*/speech',r=>{speechRequests++;return r.abort();});
  await page.goto('http://127.0.0.1:8000');await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
  const responses=[];
  for(const text of ['Okay, thanks.','Thanks, got it.','Perfect, thank you so much.']){
   await page.getByRole('textbox',{name:'Assistant request'}).fill(text);
   const response=page.waitForResponse(r=>r.url().endsWith('/commands'));
   await page.getByRole('button',{name:'Send request',exact:true}).click();
   const r=await response;const result=await r.json();
   if(!r.ok()||result.kind!=='acknowledgement'||result.trace.length||result.message!=='You’re welcome.')throw Error(JSON.stringify(result));
   responses.push({text,message:result.message,turn_id:result.turn_id});
  }
  await page.reload();await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
  await page.locator('.message.user').filter({hasText:'Okay, thanks.'}).waitFor();
  if(await page.locator('.message.assistant').count()!==3||errors.length||speechRequests)throw Error(JSON.stringify({errors,speechRequests}));
  await page.screenshot({path:'verification/acknowledgements-browser.png',fullPage:true});
  const config=await (await page.request.get('http://127.0.0.1:8000/api/config')).json();
  fs.writeFileSync('verification/acknowledgements-browser.json',JSON.stringify({buildId:config.build_id,passed:['exact Okay thanks gets local acknowledgement','compound polite variants','history persists after reload'],responses,speechRequests,pageErrors:errors,limitation:'Text-only acknowledgement path; speech muted and blocked. No microphone or STT/TTS use. Separate local matrix blocks all provider methods across empty/selected/pending/draft states.'},null,2));
  console.log('Acknowledgement UI passed. Build '+config.build_id);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
