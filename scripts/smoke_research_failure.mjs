// FAKE browser fixtures only: isolates failure rendering from provider availability.
const { chromium } = await import(process.env.CIVIS_PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';
const browser = await chromium.launch({headless:true, executablePath:process.env.CIVIS_CHROMIUM || undefined,args:['--no-sandbox']});
const page = await browser.newPage();
const errors=[];
page.on('pageerror',e=>errors.push(e.message));
let release;
const pending=new Promise(resolve=>{release=resolve;});
const conversation={id:'FAKE-chat',title:'FAKE failure',mode:'research',messages:[
 {id:'FAKE-question',role:'user',content:'FAKE question',status:'complete'},
 {id:'FAKE-answer',role:'assistant',content:'',status:'incomplete',citations:[]},
]};
await page.route('**/v1/**',async route=>{
 const path=new URL(route.request().url()).pathname;
 let json;
 if(path==='/v1/me')json={id:'FAKE-user',email:'FAKE@example.invalid',name:'FAKE',prompts_left:20,preferences:{theme:'light'}};
 else if(path==='/v1/uploads')json={items:[]};
 else if(path==='/v1/conversations')json={items:[conversation],next_cursor:null};
 else if(path==='/v1/conversations/FAKE-chat')json=conversation;
 else if(path.endsWith('/draft'))json=null;
 else if(path.endsWith('/messages')){
  await pending;
  return route.fulfill({contentType:'text/event-stream',body:'event: error\ndata: {"code":"model_unavailable","message":"Response unavailable."}\n\n'});
 }else throw new Error('Unexpected FAKE fixture request');
 await route.fulfill({json});
});
try{
 await page.goto(process.env.CIVIS_WEB_URL || 'http://localhost:53000');
 await page.locator('.msg.a p').getByText('Response unavailable.',{exact:true}).waitFor();
 await page.locator('.bar textarea').fill('FAKE retry');
 await page.getByRole('button',{name:'Send',exact:true}).click();
 await page.locator('.dots').waitFor();
 assert.equal(await page.locator('.msg.a p').count(),1,'no empty streaming paragraph');
 release();
 await page.locator('.toast').getByText('Response unavailable.',{exact:true}).waitFor();
 await page.reload();
 await page.locator('.msg.a p').getByText('Response unavailable.',{exact:true}).waitFor();
 assert.equal(await page.locator('.msg.a p').evaluateAll(nodes=>nodes.filter(n=>!n.textContent.trim()).length),0);
 assert.deepEqual(errors,[]);
 console.log('PASS: FAKE failed history/reload displays error; pending response has no blank bubble');
}finally{release();await browser.close();}
