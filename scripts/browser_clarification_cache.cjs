const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1512,height:1000}});let speechRequests=0;const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/sessions/*/speech',r=>{speechRequests++;return r.abort();});
  const navigation=await page.goto('http://127.0.0.1:8000');
  await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
  const configResponse=await page.request.get('http://127.0.0.1:8000/api/config');const config=await configResponse.json();
  if(configResponse.headers()['cache-control']!=='no-store'||!navigation.headers()['cache-control'].includes('no-cache'))throw Error('Missing cache policy');
  if(navigation.headers()['x-app-build']!==config.build_id)throw Error('Build mismatch');
  await page.locator('.build-id').filter({hasText:'Build '+config.build_id}).waitFor();
  async function send(text){
   await page.getByRole('textbox',{name:'Assistant request'}).fill(text);
   const response=page.waitForResponse(r=>r.url().endsWith('/commands'));
   await page.getByRole('button',{name:'Send request',exact:true}).click();
   const r=await response;if(!r.ok()||r.headers()['cache-control']!=='no-store')throw Error('Command/cache failure');return r.json();
  }
  const pending=await send("Hey, open Priya's latest OPG report.");
  if(pending.candidates?.length!==2)throw Error('Missing ambiguity');
  const corrected=await send("Actually it's Priya Sharma.");
  if(corrected.report?.id!=='RPT-001-03'||corrected.session.pending)throw Error('Natural clarification failed');
  const first=await send('Thank you.');const second=await send('Thank you.');
  if(first.turn_id===second.turn_id||second.replayed)throw Error('Fresh submission replayed cached turn');
  await page.reload();await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
  await page.locator('.message.user').filter({hasText:"Actually it's Priya Sharma."}).waitFor();
  if(await page.locator('.message.user').filter({hasText:'Thank you.'}).count()!==2)throw Error('Saved history not restored');
  const newSession=page.waitForResponse(r=>r.url().endsWith('/api/sessions')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'New session',exact:true}).click();await newSession;
  await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
  await send("Open Priya's latest CBCT report");
  const semantic=await send('The person I was referring to was Priya Sharma.');
  if(semantic.report?.id!=='RPT-001-02')throw Error('Semantic clarification failed: '+JSON.stringify(semantic));
  if(errors.length||speechRequests)throw Error(JSON.stringify({errors,speechRequests}));
  await page.screenshot({path:'verification/clarification-cache-browser.png',fullPage:true});
  fs.writeFileSync('verification/clarification-cache-browser.json',JSON.stringify({buildId:config.build_id,passed:['exact Actually its Priya Sharma opens original OPG','two identical submissions get different turn IDs','reload restores saved conversation','new session isolates conversation','indirect natural correction interpreted then validated opens original CBCT','page revalidates; APIs no-store; visible badge and header build agree'],freshTurnIds:[first.turn_id,second.turn_id],speechRequests,pageErrors:errors,limitation:'Live text interpretation only; no microphone or STT/TTS calls. Saved old responses are not regenerated when code changes.'},null,2));
  console.log('Natural clarification and cache/history browser checks passed. Build '+config.build_id);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
