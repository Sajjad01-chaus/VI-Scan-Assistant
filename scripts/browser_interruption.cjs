const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs'),path=require('path');
(async()=>{
 const root=path.resolve(__dirname,'..');
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||undefined,headless:true,args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
 try{
  const page=await browser.newPage();const errors=[];let commands=0;
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/commands')&&r.method()==='POST')commands++;});
  await page.addInitScript(()=>{
   window.__playCalls=0;window.__pauseCalls=0;
   const play=HTMLMediaElement.prototype.play,pause=HTMLMediaElement.prototype.pause;
   HTMLMediaElement.prototype.play=function(){window.__playCalls++;return play.call(this);};
   HTMLMediaElement.prototype.pause=function(){window.__pauseCalls++;return pause.call(this);};
  });
  await page.route('**/api/sessions/*/speech',async route=>{
   await new Promise(r=>setTimeout(r,1000));
   await route.fulfill({status:200,contentType:'audio/wav',body:fs.readFileSync(path.join(root,'verification','groq-tts-accepted-trial-1-playable.wav'))});
  });
  await page.goto('http://127.0.0.1:8000');
  await page.getByRole('checkbox',{name:'Spoken replies'}).uncheck();
  await page.locator('.patient').filter({hasText:'Priya Sharma'}).click();
  await page.getByRole('heading',{name:'Priya Sharma',exact:true}).waitFor();
  const delayed=page.waitForResponse(r=>r.url().endsWith('/speech'));
  await page.getByRole('button',{name:'Listen',exact:true}).last().click();
  await page.getByRole('button',{name:'Start microphone'}).click();
  await page.getByRole('button',{name:'Cancel recording'}).click();
  await delayed;await page.waitForTimeout(200);
  if(await page.evaluate(()=>window.__playCalls)!==0)throw new Error('Late audio restarted after interruption');
  await page.getByRole('button',{name:'Listen',exact:true}).last().click();
  await page.waitForFunction(()=>window.__playCalls===1);
  const before=await page.evaluate(()=>window.__pauseCalls);
  await page.getByRole('button',{name:'Start microphone'}).click();
  await page.getByRole('button',{name:'Cancel recording'}).click();
  const after=await page.evaluate(()=>window.__pauseCalls);
  if(after<=before)throw new Error('Microphone start did not stop playback');
  if(commands!==1)throw new Error('Cancelled captures submitted extra commands');
  if(errors.length)throw new Error(errors.join('\n'));
  fs.writeFileSync(path.join(root,'verification','browser-interruption.json'),JSON.stringify({delayedSpeechDiscarded:true,activePlaybackPaused:true,cancelledCaptureSubmittedNoCommand:true,commandRequests:commands,pageErrors:errors,method:'Browser with fake microphone and delayed synthetic TTS response; no subjective voice evaluation.'},null,2));
  console.log('Browser interruption passed: late audio discarded, active speech paused, capture cancelled.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exit(1)});
