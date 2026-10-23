const {chromium}=require('../frontend/node_modules/playwright');
const path=require('path'),fs=require('fs');
(async()=>{
 const root=path.resolve(__dirname,'..');
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||undefined,headless:true,args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',`--use-file-for-fake-audio-capture=${path.join(root,'verification','browser-microphone.wav')}`]});
 const page=await browser.newPage({viewport:{width:1512,height:1000}});const errors=[];let commandRequests=0;
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/commands'))commandRequests++;});
 await page.addInitScript(()=>{
  const original=window.fetch.bind(window);
  window.fetch=async(...args)=>{
   const response=await original(...args);
   if(response.url.endsWith('/speech')&&response.ok){
    void response.clone().arrayBuffer().then(async bytes=>{
     const ctx=new AudioContext();try{const decoded=await ctx.decodeAudioData(bytes);window.__voiceCheck={bytes:bytes.byteLength,duration:decoded.duration};}catch(e){window.__voiceCheck={error:String(e)};}finally{await ctx.close();}
    }).catch(e=>{window.__voiceCheck={error:String(e)};});
   }
   return response;
  };
 });
 await page.goto('http://127.0.0.1:8000');
 await page.getByText('Live providers',{exact:true}).waitFor();
 const speechResponse=page.waitForResponse(r=>r.url().endsWith('/speech')&&r.request().method()==='POST',{timeout:60000});
 await page.getByRole('button',{name:'Start microphone'}).click();
 await page.getByText('Stop & submit',{exact:true}).waitFor({timeout:15000});
 // Poll for actual transcript data, not a fixed delay that could stop before speech.
 await page.locator('.partial p').filter({hasText:/No evidence of a fracture/i}).waitFor({timeout:18000});
 if(process.env.AUTO_END_TEST!=='1')await page.getByRole('button',{name:'Stop and submit microphone'}).click();
 await page.locator('.message.user').waitFor({timeout:15000});
 await page.locator('.message.assistant').waitFor({timeout:20000});
 const spoken=await page.locator('.message.user').innerText();
 if(!/molar|fracture|impacted/i.test(spoken))throw new Error('No dental speech reached the command pipeline');

 const response=await speechResponse;if(response.status()!==200)throw new Error('TTS request failed');
 await page.waitForFunction(()=>!!window.__voiceCheck,undefined,{timeout:15000});
 const check=await page.evaluate(()=>window.__voiceCheck);
 if(check.error)throw new Error(check.error);
 const audioDuration=check.duration;
 if(audioDuration<=0)throw new Error('Browser could not decode generated speech');
 await page.screenshot({path:path.join(root,'verification','workspace-live-voice.png'),fullPage:true});
 if(errors.length)throw new Error(errors.join('\n'));
 if(commandRequests!==1)throw new Error('Voice must submit exactly one command');
 fs.writeFileSync(path.join(root,'verification',process.env.AUTO_END_TEST==='1'?'browser-auto-voice.json':'browser-live-voice.json'),JSON.stringify({syntheticMicrophone:true,automaticSpeechWithoutListen:true,automaticEnd:process.env.AUTO_END_TEST==='1',commandRequests,transcript:spoken,pageErrors:errors,ttsHttp:response.status(),decodedSpeechSeconds:audioDuration,limitation:'Fake Chrome microphone; not a human microphone/accent test.'},null,2));
 console.log('Browser synthetic microphone reached the live command pipeline.');await browser.close();
})().catch(e=>{console.error(e.message);process.exit(1)});
