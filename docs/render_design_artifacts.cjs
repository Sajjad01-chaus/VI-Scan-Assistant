const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs');
const path=require('path');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1050},deviceScaleFactor:1});
  for(const name of ['system-architecture','retrieval-workflow','dictation-workflow','voice-workflow']){
   const base=path.join(__dirname,'diagrams',name);
   await page.setContent('<style>body{margin:0}</style>'+fs.readFileSync(base+'.svg','utf8'));
   await page.screenshot({path:base+'.png'});
   if(name==='system-architecture'){
    await page.addStyleTag({content:'@page{size:A4 landscape;margin:0} @media print{html,body{margin:0;width:100%;height:100%}svg{display:block;width:100vw;height:100vh}}'});
    await page.pdf({path:path.join(__dirname,'architecture-one-page.pdf'),format:'A4',landscape:true,printBackground:true,margin:{top:0,right:0,bottom:0,left:0}});
   }
  }
  console.log('Rendered four PNG diagrams and one diagram-first architecture PDF. No provider calls.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
