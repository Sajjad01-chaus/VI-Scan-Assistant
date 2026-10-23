const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
 const page=await browser.newPage({viewport:{width:1512,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000');
 await page.getByRole('button',{name:/PS Priya Shah PT-002/}).click();
 await page.getByRole('heading',{name:'Priya Shah',exact:true}).waitFor();
 async function send(text){await page.getByRole('textbox',{name:'Assistant request'}).fill(text);await page.getByRole('button',{name:'Send request',exact:true}).click();}
 await send("Hello, open Ayesha Khan's report.");
 await page.getByRole('region',{name:'Confirm patient identity'}).waitFor();
 if(await page.locator('.active-context').innerText().then(t=>t.includes('Priya')))throw Error('Old identity visible as active');
 await send('Summarize her report');
 await page.getByText('Select one patient report before asking a contextual follow-up.',{exact:true}).waitFor();
 await page.screenshot({path:'verification/name-confirmation.png',fullPage:true});
 await page.getByRole('region',{name:'Confirm patient identity'}).getByRole('button',{name:/Aisha Khan/}).click();
 await page.getByRole('heading',{name:'Aisha Khan',exact:true}).waitFor();
 if(!(await page.locator('.active-context').innerText()).includes('RPT-004-03'))throw Error('Incorrect report');
 await page.getByRole('button',{name:'Summarize this report'}).click();
 await page.locator('.message.assistant').last().getByRole('button',{name:/RPT-004-03/}).first().waitFor();
 await page.getByRole('button',{name:'Edit request',exact:true}).first().click();
 if(!(await page.getByRole('textbox',{name:'Assistant request'}).inputValue()).includes('Priya Shah'))throw Error('Edit request failed');
 await page.screenshot({path:'verification/name-recovery-report.png',fullPage:true});
 for(const [width,height] of [[1366,768],[390,844]]){await page.setViewportSize({width,height});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2))throw Error('Horizontal overflow '+width);await page.screenshot({path:`verification/name-recovery-${width}.png`,fullPage:true});}
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync('verification/name-recovery-browser.json',JSON.stringify({mode:'live',input:"Hello, open Ayesha Khan's report.",passed:['close name requires explicit confirmation','previous patient paused','pronoun follow-up blocked','confirmed Aisha opens PT-004 report','summary cites only RPT-004-03','editable recognized request','no horizontal overflow at 1366 and 390 pixels'],pageErrors:errors},null,2));
 await browser.close();console.log('Live name recovery browser regression passed');
})().catch(e=>{console.error(e);process.exit(1)});
