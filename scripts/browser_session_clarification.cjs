const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true,args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
 try{
 const page=await browser.newPage({viewport:{width:1512,height:1000}});const errors=[];let captures=0;page.on('pageerror',e=>errors.push(e.message));
 await page.routeWebSocket('**/api/sessions/*/voice',ws=>{captures++;let sent=false;ws.onMessage(()=>{if(!sent){sent=true;ws.send(JSON.stringify({type:'transcript.final',text:"It's Priya Shah.",provider:'controlled-test-transcript'}));}});ws.send(JSON.stringify({type:'voice.ready'}));});
 await page.goto('http://127.0.0.1:8000');
 await page.getByRole('button',{name:'Open Priya’s latest OPG report',exact:true}).click();
 await page.getByRole('region',{name:'Confirm patient identity'}).waitFor();
 const sessionId=await page.evaluate(()=>sessionStorage.getItem('viscan-session'));
 await page.reload();await page.getByRole('region',{name:'Confirm patient identity'}).waitFor();
 if(await page.evaluate(()=>sessionStorage.getItem('viscan-session'))!==sessionId)throw Error('Refresh lost session');
 async function send(text){await page.getByRole('textbox',{name:'Assistant request'}).fill(text);const response=page.waitForResponse(r=>r.url().endsWith('/commands')&&r.status()===200);await page.getByRole('button',{name:'Send request',exact:true}).click();return (await response).json();}
 const selected=await send("It's Priya Shah.");
 await page.getByRole('heading',{name:'Priya Shah',exact:true}).waitFor();
 if(selected.report.id!=='RPT-002-03'||selected.report.modality!=='OPG')throw Error('Original request not completed');
 if(await page.getByRole('region',{name:'Confirm patient identity'}).count())throw Error('Pending UI not cleared');
 const first=await send('What is described at the upper left first molar?');
 if(first.kind!=='answer'||!first.evidence.length)throw Error('First clinical question failed');
 const followup=await send('What testing is mentioned for that tooth?');
 if(!followup.message.toLowerCase().includes('pulp testing')||followup.evidence.some(e=>e.report_id!=='RPT-002-03'))throw Error('Contextual follow-up failed: '+followup.message);
 await page.reload();await page.getByRole('heading',{name:'Priya Shah',exact:true}).waitFor();
 await page.locator('.message.user').filter({hasText:"It's Priya Shah."}).waitFor();
 await page.locator('.message.user').filter({hasText:'What testing is mentioned for that tooth?'}).waitFor();
 await page.screenshot({path:'verification/session-clarification-report.png',fullPage:true});
 await page.getByRole('button',{name:'New session',exact:true}).click();
 await page.getByRole('button',{name:'Open Priya’s latest OPG report',exact:true}).click();
 await page.getByRole('region',{name:'Confirm patient identity'}).waitFor();
 const voiceResult=page.waitForResponse(r=>r.url().endsWith('/commands')&&r.status()===200);
 await page.getByRole('button',{name:'Start microphone'}).click();
 const voice=await (await voiceResult).json();
 await page.getByRole('heading',{name:'Priya Shah',exact:true}).waitFor();
 if(voice.report.id!=='RPT-002-03'||captures!==1)throw Error('Voice clarification failed');
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync('verification/session-clarification-browser.json',JSON.stringify({passed:['original ambiguous OPG request','pending choices survive refresh in same session','typed Its Priya Shah opens PT-002 original OPG','follow-up resolves that tooth and cites current report','chat and selected report survive refresh','new session starts clean','controlled microphone transcript Its Priya Shah resolves selection'],captures,pageErrors:errors,limitation:'LLM requests are live; voice clarification uses an injected STT final transcript to reproduce the exact user text. Human STT recognition and OS audio output are not asserted.'},null,2));
 console.log('Session clarification, refresh recovery and live contextual follow-up passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
