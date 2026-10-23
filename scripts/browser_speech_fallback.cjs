const {chromium}=require('../frontend/node_modules/playwright');const fs=require('fs');
(async()=>{const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{
  window.__localSpeech=[];window.__cancelCount=0;
  class Utterance extends EventTarget{constructor(text){super();this.text=text;}}
  Object.defineProperty(window,'SpeechSynthesisUtterance',{value:Utterance,configurable:true});
  const synthesis=new EventTarget();synthesis.getVoices=()=>[{name:'Test local voice',lang:'en-IN'}];
  synthesis.speak=utterance=>{window.__localSpeech.push(utterance.text);utterance.onstart?.(new Event('start'));};
  synthesis.cancel=()=>window.__cancelCount++;
  Object.defineProperty(window,'speechSynthesis',{value:synthesis,configurable:true});
 });
 await page.route('**/api/sessions/*/speech',route=>route.fulfill({status:503,json:{detail:'Controlled cloud quota outage'}}));
 await page.goto('http://127.0.0.1:8000');
 await page.locator('.patient').filter({hasText:'Priya Shah'}).click();
 await page.getByRole('heading',{name:'Priya Shah',exact:true}).waitFor();
 await page.getByText('Browser voice — cloud speech unavailable',{exact:true}).waitFor();
 await page.waitForFunction(()=>window.__localSpeech.some(t=>t.includes('Opened Priya Shah')));
 const question='Can you summarize it like what happened to her? What is her main cause?';
 await page.getByRole('textbox',{name:'Assistant request'}).fill(question);await page.getByRole('button',{name:'Send request',exact:true}).click();
 await page.waitForFunction(()=>window.__localSpeech.some(t=>t.includes('underlying cause')));
 const spoken=await page.evaluate(()=>window.__localSpeech.at(-1));
 if(spoken!==(await page.locator('.message.assistant p').last().innerText()))throw Error('Fallback did not use the exact displayed answer');
 const cancelled=await page.evaluate(()=>window.__cancelCount);
 await page.getByRole('button',{name:'Stop speech',exact:true}).click();
 if(await page.evaluate(()=>window.__cancelCount)<=cancelled)throw Error('Browser speech did not stop');
 const before=await page.evaluate(()=>window.__localSpeech.length);
 await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
 await page.locator('.patient').filter({hasText:'Aisha Khan'}).click();await page.getByRole('heading',{name:'Aisha Khan',exact:true}).waitFor();
 if(await page.evaluate(()=>window.__localSpeech.length)!==before)throw Error('Mute did not suppress fallback');
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync('verification/browser-speech-fallback.json',JSON.stringify({passed:['cloud failure triggers disclosed browser voice','fallback uses exact displayed answer','compound answer includes unknown cause','stop cancels browser voice','mute suppresses fallback'],spoken,pageErrors:errors,limitation:'Browser speech API and cloud outage are controlled test doubles. This verifies app integration, not installed voice availability or human audibility; the headless inventory had no native voices.'},null,2));
 console.log('Browser-voice fallback integration passed');
 }finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
