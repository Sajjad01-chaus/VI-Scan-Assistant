const {chromium}=require('../frontend/node_modules/playwright');const fs=require('fs');
(async()=>{const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});try{
 const page=await browser.newPage({viewport:{width:1512,height:1000}});let speechAttempts=0;const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/sessions/*/speech',route=>{speechAttempts++;return route.fulfill({status:503,json:{detail:'Test blocks all cloud speech'}});});
 await page.goto('http://127.0.0.1:8000');await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
 async function send(text){const result=page.waitForResponse(r=>r.url().endsWith('/commands')&&r.status()===200);await page.getByRole('textbox',{name:'Assistant request'}).fill(text);await page.getByRole('button',{name:'Send request',exact:true}).click();return (await result).json();}
 const opened=await send("Hey, can you open Meera Iyer's report?");if(opened.report?.id!=='RPT-006-03')throw Error('Wrong report opened');
 const question='Have you find any key findings in her report?';const answer=await send(question);
 fs.writeFileSync('verification/meera-key-findings.json',JSON.stringify({question,response:answer,speechAttempts,method:'Live text-only LLM calls; speech muted and all speech endpoints intercepted; no microphone used.'},null,2));
 if(answer.kind!=='answer'||!answer.evidence.length||!/No definite/i.test(answer.message)||/not stated|cannot infer/i.test(answer.message))throw Error('Key findings still rejected: '+answer.message);
 if(answer.evidence.some(e=>e.report_id!=='RPT-006-03'||!answer.session.report.content.includes(e.quote)))throw Error('Invalid evidence');
 if(speechAttempts||errors.length)throw Error(JSON.stringify({speechAttempts,errors}));
 await page.screenshot({path:'verification/meera-key-findings.png',fullPage:true});
 console.log(answer.message);console.log('Exact Meera exchange passed; zero STT/TTS calls.');
 }finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
