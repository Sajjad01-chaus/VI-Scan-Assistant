const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
 try{
 const page=await browser.newPage({viewport:{width:1512,height:1000}});const errors=[];let speechRequests=0;
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/speech'))speechRequests++;});
 await page.addInitScript(()=>{
  window.__playing=0;window.__advanced=0;window.__fallbackStarted=0;window.__forceBlocked=false;


  const play=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){this.addEventListener('playing',()=>window.__playing++);this.addEventListener('timeupdate',()=>{if(this.currentTime>.05&&!this.muted&&this.volume>0)window.__advanced++;});if(window.__forceBlocked)return Promise.reject(new DOMException('Test autoplay restriction','NotAllowedError'));return play.call(this);};
  const start=AudioBufferSourceNode.prototype.start;AudioBufferSourceNode.prototype.start=function(...args){window.__fallbackStarted++;return start.apply(this,args);};
 });
 await page.goto('http://127.0.0.1:8000');
 const spoken=page.getByRole('checkbox',{name:'Spoken replies'});if(!await spoken.isChecked())throw Error('Speech is not on by default');
 await page.locator('.patient').filter({hasText:'Arjun Mehta'}).click();
 await page.getByRole('heading',{name:'Arjun Mehta',exact:true}).waitFor();
 await page.waitForFunction(()=>window.__advanced>0,undefined,{timeout:45000});
 if(await page.locator('.document-section').count()!==7)throw Error('Not a full report');
 if((await page.locator('.report-document').innerText()).length<1200)throw Error('Report too short');
 for(const name of ['Clinical Indication','Technique','Comparison','Findings','Impression','Clinical Correlation','Limitations'])await page.getByRole('heading',{name,exact:true}).waitFor();
 const before=await page.evaluate(()=>window.__playing);
 await page.getByRole('button',{name:'Summarize this report'}).click();
 await page.waitForFunction(n=>window.__playing>n,before,{timeout:45000});
 await spoken.uncheck();const mutedRequests=speechRequests;
 await page.locator('.patient').filter({hasText:'Aisha Khan'}).click();
 await page.getByRole('heading',{name:'Aisha Khan',exact:true}).waitFor();
 if(speechRequests!==mutedRequests)throw Error('Muted action requested speech');
 await spoken.check();await page.evaluate(()=>window.__forceBlocked=true);
 await page.locator('.patient').filter({hasText:'Arjun Mehta'}).click();
 await page.waitForFunction(()=>window.__fallbackStarted>0,undefined,{timeout:45000});
 await page.getByText('Speakingâ€¦',{exact:true}).waitFor();
 await page.screenshot({path:'verification/full-report-speaking.png',fullPage:true});
 await page.route('**/api/sessions/*/speech',route=>route.fulfill({status:503,json:{detail:'Forced speech outage'}}));
 await page.locator('.patient').filter({hasText:'Aisha Khan'}).click();
 await page.getByRole('heading',{name:'Aisha Khan',exact:true}).waitFor();
 await page.getByText('Spoken reply unavailable â€” use Listen to retry.',{exact:true}).waitFor();
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync('verification/default-speech-full-reports.json',JSON.stringify({passed:['speech enabled by default','directory selection automatically plays audio without Listen','audio currentTime advances unmuted','typed summary automatically plays audio','seven report sections and substantial content','mute suppresses speech requests','forced HTML autoplay rejection falls back to unlocked Web Audio','forced TTS outage retains selected report and visible retry status'],speechRequests,pageErrors:errors,limitation:'Headless Chrome playback events and progress; does not verify the user OS output device, volume or subjective audibility.'},null,2));
 console.log('Default speech, playback progress, report sections, mute, autoplay fallback and outage checks passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
