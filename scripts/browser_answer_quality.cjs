const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
 try{
 const page=await browser.newPage({viewport:{width:1512,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{
  window.__playedTurns=[];window.__speechTurn='';const fetch=window.fetch.bind(window);
  window.fetch=async(...args)=>{const response=await fetch(...args);if(response.ok&&response.url.endsWith('/speech'))window.__speechTurn=JSON.parse(args[1].body).turn_id;return response;};
  const play=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){const turn=window.__speechTurn;this.addEventListener('playing',()=>window.__playedTurns.push(turn),{once:true});return play.call(this);};
 });
 await page.goto('http://127.0.0.1:8000');
 if(process.env.TEXT_ONLY==='1')await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
 await page.getByRole('button',{name:'Open Priya’s latest OPG report',exact:true}).click();
 await page.getByRole('region',{name:'Confirm patient identity'}).waitFor();
 async function send(text){const result=page.waitForResponse(r=>r.url().endsWith('/commands')&&r.status()===200);await page.getByRole('textbox',{name:'Assistant request'}).fill(text);await page.getByRole('button',{name:'Send request',exact:true}).click();return (await result).json();}
 await send("It's Priya Shah.");await page.getByRole('heading',{name:'Priya Shah',exact:true}).waitFor();
 const request='Can you summarize it like what happened to her? What is her main cause?';
 const answer=await send(request);
 if(answer.kind!=='answer')throw Error(JSON.stringify(answer));
 if(!answer.cause_not_established||!answer.message.includes('underlying cause'))throw Error('Cause was not explicitly addressed');
 if(!/possible|uncertain/i.test(answer.message)||!answer.message.includes('darker area'))throw Error('Missing uncertainty or plain terminology: '+answer.message);
 if(answer.message.split(/\s+/).length>100||answer.evidence.length>3||!answer.evidence.length)throw Error('Not concise/cited');
 if(answer.evidence.some(e=>e.report_id!=='RPT-002-03'||!answer.session.report.content.includes(e.quote)))throw Error('Wrong evidence');
 if(process.env.TEXT_ONLY!=='1')await page.waitForFunction(id=>window.__playedTurns.includes(id),answer.turn_id,{timeout:45000});
 await page.screenshot({path:'verification/concise-summary-cause.png',fullPage:true});
 const unsupported=await send('Does her report confirm oral cancer?');
 if(unsupported.kind!=='answer'||unsupported.evidence.length||!/not stated|cannot infer/i.test(unsupported.message)){fs.writeFileSync('verification/answer-quality-failure.json',JSON.stringify({request,response:answer,unsupported},null,2));throw Error('Unsupported diagnosis not refused: '+JSON.stringify({message:unsupported.message,trace:unsupported.trace}));}
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync('verification/concise-summary-cause.json',JSON.stringify({request,response:answer,unsupportedQuestion:{message:unsupported.message,evidence:unsupported.evidence},passed:['original compound question preserved','concise main finding','uncertainty retained','explicit unknown cause','at most three exact current-report citations',...(process.env.TEXT_ONLY==='1'?['speech checked separately; cloud quota unavailable']:['automatic live TTS playing event for this turn']),'unsupported diagnosis abstained'],pageErrors:errors,limitation:'Small synthetic report scenario and headless playback event; not clinical validation or human audio evaluation.'},null,2));
 console.log(answer.message);console.log('Concise summary/cause and automatic speech checks passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
