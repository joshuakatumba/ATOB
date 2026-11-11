// External QA dependency only; no frontend dependency changes.
const { chromium } = await import(process.env.CIVIS_PLAYWRIGHT_MODULE || "playwright");
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const browser = await chromium.launch({headless:true, executablePath:process.env.CIVIS_CHROMIUM || undefined,args:['--no-sandbox']});
const page = await browser.newPage({acceptDownloads:true, viewport:{width:1440,height:1000}});
const errors=[];
page.on('pageerror', e=>errors.push(e.message));
page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('401'))errors.push(m.text());});
page.on('dialog', d=>d.accept());
try {
 await page.goto(process.env.CIVIS_WEB_URL || 'http://localhost:53000');
 await page.getByRole('button',{name:'Sign up',exact:true}).click();
 await page.getByLabel('Full name').fill('FAKE Browser');
 await page.getByLabel('Email',{exact:true}).fill(`FAKE-${crypto.randomUUID()}@example.invalid`);
 await page.getByLabel('Password',{exact:true}).fill('FAKE-a1-'+crypto.randomBytes(24).toString('hex'));
 const signup=page.waitForResponse(r=>r.url().endsWith('/auth/signup'));
 await page.getByRole('button',{name:'Create account',exact:true}).click();
 assert.equal((await signup).status(),200,'QA signup HTTP status');
 await page.locator('.bar textarea').fill(process.env.CIVIS_RESEARCH_QUERY || 'Give one short factual statement from a retrieved employment source, without advice.');
 const stream=page.waitForResponse(r=>r.url().endsWith('/messages')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'Send',exact:true}).click();
 const response=await stream;
 assert.equal(response.status(),200);
 await Promise.race([
   page.locator('.msg.a p a[href^="https://ulii.org/akn/ug/"]').first().waitFor({timeout:130000}),
   page.locator('.toast').waitFor({timeout:130000}).then(() => { throw new Error('Research returned an error; no verified answer'); }),
 ]);
 const count=await page.locator('.msg.a p a').count();
 assert.ok(count>0);
 await page.reload();
 await page.locator('.msg.a p a[href^="https://ulii.org/akn/ug/"]').first().waitFor({timeout:130000});
 assert.equal(await page.locator('.msg.a p a').count(),count);
 // FAKE UI fixture: an interrupted response restored from history must not be blank.
 const path=new URL(response.url()).pathname.replace(/\/messages$/, '');
 const detail=await (await page.request.get(new URL(path,page.url()).href)).json();
 detail.messages.push({id:crypto.randomUUID(),role:'assistant',content:'',status:'incomplete',created_at:new Date().toISOString(),citations:[]});
 await page.route('**'+path, route=>route.fulfill({json:detail}));
 await page.reload();
 await page.getByText('Response unavailable.',{exact:true}).waitFor();
 assert.equal(await page.locator('.msg.a .b p').evaluateAll(nodes=>nodes.filter(n=>!n.textContent.trim()).length),0);
 assert.deepEqual(errors,[]);
 console.log('PASS: live hosted Uganda retrieval/Groq verification, citation links, reload, failed-message UI, no browser errors');
} finally {await browser.close();}
