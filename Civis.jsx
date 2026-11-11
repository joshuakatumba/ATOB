import { useEffect, useMemo, useRef, useState } from "react";

/*
  Civis: single-file React version of the prototype.
  Default export <App/>. Needs React 18+ and nothing else (styles are injected below).
  State is in memory only. Seams to replace with the real backend are marked SEAM.
*/

/* ------------------------------- data ---------------------------------- */

const TPL = {
  "Employment & workplace": ["Employment Contract Agreement", "Disciplinary Form", "Termination Letter", "Offer Letter", "Non-Compete Agreement", "Leave Request Form", "Internship Agreement", "Probation Letter", "Redundancy Notice", "Employee Handbook", "Resignation Letter"],
  "Property & tenancy": ["Lease Agreement", "Real Estate Property Power of Attorney", "Notice to Vacate", "Rent Receipt", "Property Sale Agreement"],
  "Sale, supply & commercial": ["Business Sale Agreement", "Supply Agreement", "Distribution Agreement", "Agency Agreement", "Purchase Order Terms"],
  "Professional services": ["Freelance Service Agreement", "Consulting Agreement", "Statement of Work", "Retainer Agreement"],
  "Notices & letters": ["Demand Letter", "Cease and Desist Letter", "Notice of Breach", "Formal Complaint Letter"],
  "Company policies": ["Anti-Bribery and Corruption Policy", "Anti-Money Laundering Policy", "Anti-Slavery Policy Statement", "Anti-Spam Policy", "Cell Phone Policy", "Clean Desk Policy", "Company Credit Card Policy", "Competition Terms & Conditions", "Cookie Policy", "Privacy Policy", "Code of Conduct", "Remote Work Policy", "Data Protection Policy", "Social Media Policy", "Whistleblowing Policy", "Health and Safety Policy", "Equal Opportunities Policy"],
  "Affidavits, powers of attorney & family": ["Affidavit of Support", "General Power of Attorney", "Will", "Child Custody Agreement"],
  "IP, media & licences": ["Software Licence Agreement", "Copyright Assignment", "Trademark Licence", "Photo Release Form"],
  "Finance, invoices & receipts": ["Invoice", "Loan Agreement", "Payment Receipt", "IOU Note"],
  "Judgments & rulings": ["Court Judgment"],
  "Pleadings & court process": ["Statement of Claim", "Statement of Defence", "Notice of Motion"],
};
const POP = ["Lease Agreement", "Employment Contract Agreement", "Court Judgment", "Real Estate Property Power of Attorney", "Business Sale Agreement", "Disciplinary Form"];

/* Placeholder wording only. Real template text must come from reviewed legal content. */
const KINDS = {
  agreement: {
    f: [["a", "First party name", "Bright Builders Ltd"], ["aa", "First party address", "Plot 50, Ntinda Road, Kampala, Uganda"], ["b", "Second party name", "Grace Nakimera"], ["ba", "Second party address", "Plot 27, Jinja Road, Kampala, Uganda"], ["d1", "Effective date", "2026-12-01"], ["d2", "End date", "2027-03-01"], ["amt", "Amount", "UGX 5,000,000"], ["det", "Key terms", "The work will be completed within 90 days."], ["law", "Governing law", "Laws of the Republic of Uganda"]],
    b: [["PARTIES", "This {T} is made on {d1} between {a}, of {aa} (the \u201cFirst Party\u201d), and {b}, of {ba} (the \u201cSecond Party\u201d)."], ["TERM", "This agreement starts on {d1} and ends on {d2} unless it is ended earlier under its terms."], ["KEY TERMS", "{det}"], ["PAYMENT", "The agreed amount is {amt}. Payment is due as the parties agree in writing."], ["TERMINATION", "Either party may end this agreement by written notice if the other party breaks it and does not fix the problem within 14 days."], ["GOVERNING LAW", "This agreement is governed by the {law}."], ["SIGNATURES", "Signed by {a} and {b} on {d1}."]],
  },
  letter: {
    f: [["a", "Sender name", "Grace Nakimera"], ["aa", "Sender address", "Plot 27, Jinja Road, Kampala, Uganda"], ["b", "Recipient name", "Kevin Odoch"], ["ba", "Recipient address", "Plot 15, Kira Road, Kampala, Uganda"], ["d1", "Date", "2026-12-01"], ["sub", "Subject", "Subject of this document"], ["det", "Details", "Explain the matter clearly and what you want to happen."], ["d2", "Respond by", "2026-12-15"]],
    b: [["", "From: {a}, {aa}"], ["", "To: {b}, {ba}"], ["", "Date: {d1}"], ["SUBJECT", "{sub}"], ["", "Dear {b},"], ["", "{det}"], ["", "Please respond or act by {d2}."], ["", "Yours sincerely, {a}"]],
  },
  policy: {
    f: [["a", "Company name", "Bright Builders Ltd"], ["aa", "Company address", "Plot 50, Ntinda Road, Kampala, Uganda"], ["d1", "Effective date", "2026-12-01"], ["own", "Policy owner", "Kevin Odoch"], ["scope", "Who this applies to", "All employees, contractors and visitors"], ["det", "Key commitments", "We follow the law and treat everyone fairly and with respect."], ["em", "Contact email", "legal@brightbuilders.example"]],
    b: [["PURPOSE", "This {T} sets out how {a}, of {aa}, handles this matter."], ["SCOPE", "This policy applies to {scope}."], ["POLICY", "{det}"], ["RESPONSIBILITY", "{own} is responsible for this policy and for keeping it up to date."], ["EFFECTIVE DATE", "This policy takes effect on {d1}."], ["CONTACT", "Questions about this policy go to {em}."]],
  },
  declaration: {
    f: [["a", "Full name", "Grace Nakimera"], ["aa", "Address", "Plot 27, Jinja Road, Kampala, Uganda"], ["b", "Other person (agent, beneficiary or witness)", "Kevin Odoch"], ["ba", "Other person\u2019s address", "Plot 15, Kira Road, Kampala, Uganda"], ["d1", "Date", "2026-12-01"], ["det", "Statement or instructions", "State the facts or instructions you want recorded."], ["law", "Governing law", "Laws of the Republic of Uganda"]],
    b: [["DECLARATION", "I, {a}, of {aa}, make this {T} on {d1}."], ["OTHER PERSON", "This document names {b}, of {ba}."], ["DETAILS", "{det}"], ["GOVERNING LAW", "This document is governed by the {law}."], ["SIGNATURE", "Signed by {a} on {d1} in the presence of {b}."]],
  },
  court: {
    f: [["court", "Court name", "High Court of Uganda at Kampala"], ["cn", "Case number", "HCCS No. 123 of 2026"], ["a", "Claimant", "Grace Nakimera"], ["b", "Defendant", "Bright Builders Ltd"], ["d1", "Date", "2026-12-01"], ["det", "Facts", "Set out the facts of the case in order."], ["rel", "Relief sought", "Payment of UGX 5,000,000 and costs of the suit."]],
    b: [["COURT", "In the {court}, {cn}."], ["PARTIES", "Between {a} (Claimant) and {b} (Defendant)."], ["FACTS", "{det}"], ["RELIEF", "The Claimant asks the court for: {rel}"], ["DATE", "Dated {d1}."]],
  },
  finance: {
    f: [["a", "Payee name", "Bright Builders Ltd"], ["b", "Payer name", "Grace Nakimera"], ["d1", "Date", "2026-12-01"], ["amt", "Amount", "UGX 5,000,000"], ["det", "Description", "Payment for services provided"], ["pm", "Payment method", "Mobile money"]],
    b: [["DATE", "{d1}"], ["FROM", "{b}"], ["TO", "{a}"], ["AMOUNT", "{amt}"], ["FOR", "{det}"], ["PAYMENT METHOD", "{pm}"]],
  },
};

function kindOf(n, cat) {
  if (cat === "Notices & letters") return "letter";
  if (cat === "Company policies") return "policy";
  if (cat === "Affidavits, powers of attorney & family") return "declaration";
  if (cat === "Pleadings & court process" || cat === "Judgments & rulings") return "court";
  if (/Agreement|Assignment|Licence|Terms|Statement of Work/.test(n)) return "agreement";
  if (/Receipt|Invoice|IOU/.test(n)) return "finance";
  if (/Power of Attorney/.test(n)) return "declaration";
  if (/Letter|Notice|Form$|Handbook/.test(n)) return "letter";
  return "agreement";
}
const catOf = (n) => Object.keys(TPL).find((c) => TPL[c].includes(n)) || "";
const valOf = (d, k) => (k === "T" ? d.name : (d.vals[k] || "").trim() || "n/a");
const plain = (p, d) => p.replace(/\{(\w+)\}/g, (_, k) => valOf(d, k));
const slug = (s) => s.replace(/[^A-Za-z0-9]+/g, "_");
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function Filled({ p, d }) {
  return p.split(/(\{\w+\})/).map((s, i) => {
    const m = s.match(/^\{(\w+)\}$/);
    return m ? <span key={i} className="v">{valOf(d, m[1])}</span> : s;
  });
}

/* Browser-side stand-in. Real .docx must be rendered on the server so preview and file match. */
function downloadDoc(d) {
  const K = KINDS[d.kind];
  const body = `<h2 style="text-align:center">${esc(d.name.toUpperCase())}</h2>` + K.b.map(([h, p]) => (h ? `<h4>${h}</h4>` : "") + `<p>${esc(plain(p, d))}</p>`).join("");
  const html = `<html><head><meta charset="utf-8"></head><body>${body}</body></html>`;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["\ufeff", html], { type: "application/msword" }));
  a.download = slug(d.name) + ".doc";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

/* ------------------------------ SEAMS ---------------------------------- */

const IDEAS = {
  research: ["What are my rights if I am dismissed without notice?", "Explain the main clauses in an NDA", "How long do I have to file a claim for unpaid wages?", "Trademark or copyright for my brand name?"],
};
const CANNED = {
  research: ["Here is how this usually works. The exact rules depend on where you are, so tell me the country or state and I can be more specific. Start by collecting the documents that relate to the issue, such as contracts, messages and receipts, and note the key dates.", "A sensible first step is to put your position in writing and keep a record of every exchange. From there the options are normally negotiation, mediation or a formal claim. If a deadline is close, speak to a licensed lawyer soon."],
  drafting: ["I can prepare this. Tell me who the parties are, the key dates and amounts, and any terms you want included. I will then write a full draft you can edit."],
};
/* SEAM: replace with POST /v1/conversations/{id}/messages (streaming). */
async function askCivis({ mode }) {
  await new Promise((r) => setTimeout(r, 1000));
  const list = CANNED[mode];
  return list[Math.floor(Math.random() * list.length)];
}
/* SEAM: replace with real auth (sign up, verify, log in, reset, log out). */
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* ignore */ } },
  del(k) { try { localStorage.removeItem(k); } catch (e) { /* ignore */ } },
};
/* Prototype only: accounts live in this browser. Passwords are hashed but this is not real security. */
const ACCOUNTS = store.get("civis-accounts", {});
async function hashPw(s) {
  try {
    const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("civis:" + s));
    return Array.from(new Uint8Array(b)).map((x) => x.toString(16).padStart(2, "0")).join("");
  } catch (e) { return "p:" + btoa(unescape(encodeURIComponent(s))); }
}

/* ------------------------------- icons --------------------------------- */

const IC = {
  panelClose: "M5 4h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zM9 4v16M16 10l-2 2 2 2",
  panelOpen: "M5 4h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zM9 4v16M14 10l2 2-2 2",
  edit: "M12 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-6M18 3l3 3-8 8-4 1 1-4z",
  doc: "M6 3h8l4 4v14H6zM14 3v4h4M9 12h6M9 16h6",
  draft: "M14 3H6v18h12v-8M14 3l4 4h-4zM12 17l1-3 7-7 2 2-7 7z",
  book: "M3 5h7a2 2 0 0 1 2 2v13a2 2 0 0 0-2-2H3zM21 5h-7a2 2 0 0 0-2 2v13a2 2 0 0 1 2-2h7z",
  clock: "M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2",
  gem: "M6 3h12l4 6-10 12L2 9zM2 9h20M9 3l3 6 3-6",
  users: "M9 4.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7zM3 20c0-3.3 2.7-6 6-6s6 2.7 6 6M19 8v6M16 11h6",
  mail: "M5 5h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2zM3 7l9 6 9-6",
  down: "M12 3v12m-5-5 5 5 5-5M4 20h16",
  moon: "M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z",
  shield: "M12 3 4 6v6c0 4.5 3.2 7.8 8 9 4.8-1.2 8-4.5 8-9V6z",
  share: "M14 4h6v6M20 4l-9 9M18 14v5H5V6h5",
  out: "M10 4H5v16h5M15 8l4 4-4 4M19 12H9",
  x: "M6 6l12 12M18 6 6 18",
  mic: "M12 3a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM5 11a7 7 0 0 0 14 0M12 18v3",
  info: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 11v5M12 8h.01",
  search: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4",
  up: "m6 15 6-6 6 6",
};
const Icon = ({ n }) => (
  <svg className="i" viewBox="0 0 24 24" aria-hidden="true"><path d={IC[n]} /></svg>
);

/* ------------------------------- styles -------------------------------- */

const CSS = `
.cv{--bg:#fff;--side:#f7f7f8;--line:#e8e8ea;--ink:#16181d;--mute:#6b7078;--accent:#1f3a5f;--hover:#eeeff1;--bubble:#f1f2f4;--card:#fff;--soft:#3a3e46;--on:#e9ebef;--bd2:#d9dbe0;--pop:#fff;height:100vh;height:100dvh;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;box-sizing:border-box;overflow:hidden}
.cv.dark{--bg:#16181d;--side:#1d2026;--line:#2b2f37;--ink:#eceef2;--mute:#9aa0aa;--accent:#5f8cc4;--hover:#272b33;--bubble:#262a32;--card:#22262d;--soft:#c5c9d0;--on:#2d323b;--bd2:#3a3f48;--pop:#23272e}
.cv *,.cv *::before,.cv *::after{box-sizing:inherit}
:where(.cv button){font:inherit;color:inherit;cursor:pointer;border:0;background:none}
.cv button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
:where(.cv textarea,.cv input){font:inherit;color:var(--ink);outline:0}
.cv .i{width:18px;height:18px;flex:none;stroke:currentColor;fill:none;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
.app{display:flex;height:100%}
.side{width:268px;flex:none;background:var(--side);border-right:1px solid var(--line);display:flex;flex-direction:column;padding:14px 10px;transition:margin .2s}
.side.min{width:60px;align-items:center;padding:14px 8px}
.brandrow{display:flex;align-items:center;justify-content:space-between}
.brand{font:600 22px Georgia,"Times New Roman",serif;color:var(--accent);padding:4px 10px 14px}
.ic{width:34px;height:34px;display:grid;place-items:center;border-radius:50%;color:var(--mute);flex:none}
.ic:hover,.subl:hover{background:var(--hover)}
.rail{display:flex;flex-direction:column;align-items:center;gap:8px}
.new{display:flex;align-items:center;gap:8px;width:100%;padding:9px 10px;border-radius:9px;border:1px solid var(--line);background:var(--card);font-weight:500}
.new:hover{background:var(--hover)}
.modes{display:flex;gap:4px;padding:4px;background:var(--hover);border-radius:12px;margin-top:10px}
.mode{flex:1;display:flex;align-items:center;justify-content:center;gap:7px;padding:7px 6px;border-radius:9px;color:var(--mute);font-weight:500;font-size:14px}
.mode.on{background:var(--card);color:var(--ink);box-shadow:0 1px 3px rgba(0,0,0,.1)}
.list{flex:1;overflow-y:auto;margin:14px 0;display:flex;flex-direction:column;gap:2px}
.chat{text-align:left;padding:8px 10px;border-radius:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--soft)}
.chat:hover{background:var(--hover)}
.chat.on{background:var(--on);color:var(--ink)}
.acct{position:relative;border-top:1px solid var(--line);margin:0 -10px;padding:8px 10px 0}
.me{display:flex;align-items:center;gap:10px;width:100%;padding:8px 10px;border-radius:9px;text-align:left}
.me:hover{background:var(--hover)}
.av{width:30px;height:30px;border-radius:50%;background:var(--accent);color:#fff;display:grid;place-items:center;font-size:13px;font-weight:600;flex:none}
.who{flex:1;min-width:0}
.who b{display:block;font-weight:600;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.who i{display:block;font-style:normal;color:var(--mute);font-size:13px}
.pop{position:absolute;left:10px;right:10px;bottom:calc(100% + 6px);background:var(--pop);border:1px solid var(--line);border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,.14);padding:8px;z-index:5}
.mail{padding:8px 10px;color:var(--mute);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.it{display:flex;align-items:center;gap:12px;width:100%;padding:9px 10px;border-radius:9px;text-align:left}
.it:hover{background:var(--hover)}
.sep{height:1px;background:var(--line);margin:6px 4px}
.main{flex:1;min-width:0;display:flex;flex-direction:column}
.top{display:none;align-items:center;gap:10px;padding:10px 14px;border-bottom:1px solid var(--line)}
.scroll{flex:1;overflow-y:auto}
.wrap{max-width:900px;margin:0 auto;padding:28px 20px 12px}
.hero{max-width:720px;margin:0 auto;min-height:52vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:22px}
.hero h1{font:500 34px/1.2 Georgia,"Times New Roman",serif;margin:0;max-width:16em}
.ideas{display:grid;grid-template-columns:1fr 1fr;gap:10px;width:100%;max-width:560px}
.idea{text-align:left;padding:12px 14px;border:1px solid var(--line);border-radius:12px;color:var(--soft);font-size:14px}
.idea:hover{background:var(--side)}
.msg{display:flex;margin:18px auto;max-width:720px}
.msg.u{justify-content:flex-end}
.msg.u .b{background:var(--bubble);padding:9px 15px;border-radius:18px;max-width:80%}
.msg.a{gap:12px}
.mk{width:28px;height:28px;flex:none;border-radius:8px;background:var(--accent);color:#fff;display:grid;place-items:center;font:600 14px Georgia,serif;margin-top:2px}
.msg.a .b{min-width:0}
.msg.a p{margin:0 0 10px;white-space:pre-wrap}
.btn{padding:8px 16px;border-radius:10px;border:1px solid var(--bd2);background:var(--card)}
.btn.pri{background:var(--accent);color:#fff;border-color:var(--accent)}
.dots span{display:inline-block;width:6px;height:6px;margin-right:4px;border-radius:50%;background:#b5b9c1;animation:cvd 1s infinite}
.dots span:nth-child(2){animation-delay:.15s}.dots span:nth-child(3){animation-delay:.3s}
@keyframes cvd{50%{opacity:.25}}
.bar{padding:8px 20px 14px}
.box{max-width:720px;margin:0 auto;border:1px solid var(--bd2);border-radius:22px;display:flex;flex-direction:column;gap:2px;padding:14px 12px 10px 18px;background:var(--card);box-shadow:0 1px 6px rgba(20,24,35,.05)}
.box.wide{max-width:900px}
.box:focus-within{border-color:var(--mute)}
.box textarea{border:0;resize:none;max-height:160px;padding:2px 0 8px;background:transparent;width:100%}
.tools{display:flex;align-items:center;gap:6px}
.sp{flex:1}
.subl{display:flex;align-items:center;gap:7px;font-weight:600;font-size:14px;padding:6px 10px;border-radius:9px}
.send{width:34px;height:34px;border-radius:50%;background:var(--accent);color:#fff;display:grid;place-items:center;flex:none}
.send:disabled{background:#d5d8de;cursor:default}
.note{text-align:center;color:var(--mute);font-size:12px;margin:8px 0 0}
.voice{display:flex;flex-direction:column;gap:10px}
.vt{min-height:22px;color:var(--mute);font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.vr{display:flex;align-items:center;gap:8px}
.wv{flex:1;display:flex;align-items:center;gap:3px;height:38px}
.wv i{flex:1;max-width:5px;height:100%;border-radius:3px;background:var(--accent);transform:scaleY(.15)}
.tpl{padding-top:8px}
.ts{display:flex;align-items:center;gap:10px;border:1px solid var(--bd2);border-radius:16px;padding:0 16px;background:var(--card)}
.ts:focus-within{border-color:var(--mute)}
.ts input{flex:1;border:0;background:transparent;padding:15px 0}
.chips{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin:16px 0 20px}
.chip{border:1px solid var(--line);border-radius:999px;padding:6px 14px;color:var(--soft);font-size:14px;background:var(--card)}
.chip em{font-style:normal;color:var(--mute);font-size:12px;margin-left:4px}
.chip:hover{background:var(--hover)}
.chip.on{background:var(--accent);border-color:var(--accent);color:#fff}
.chip.on em{color:#dfe7f2}
.tg{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.tc{display:flex;align-items:center;gap:12px;text-align:left;border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:var(--card);min-width:0}
.tc:hover{border-color:var(--mute)}
.tc .i{color:var(--mute)}
.tc span{min-width:0}
.tc b,.fm b{display:block;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tc i,.fm i{display:block;font-style:normal;color:var(--mute);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.none{grid-column:1/-1;text-align:center;color:var(--mute)}
.more{grid-column:1/-1;justify-self:center;padding:8px 16px;color:var(--soft);font-weight:500;border-radius:9px}
.more:hover{background:var(--hover)}
.panel{width:46%;max-width:620px;min-width:380px;flex:none;border-left:1px solid var(--line);display:flex;flex-direction:column;background:var(--bg)}
.ph{display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--line)}
.ph h2{flex:1;min-width:0;margin:0;font:500 18px Georgia,serif;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.seg{display:flex;padding:3px;background:var(--hover);border-radius:10px}
.seg button{padding:5px 12px;border-radius:8px;color:var(--mute);font-size:14px}
.seg button.on{background:var(--card);color:var(--ink);box-shadow:0 1px 3px rgba(0,0,0,.1)}
.gen{background:var(--ink);color:var(--bg);padding:8px 16px;border-radius:10px;font-weight:600;font-size:14px}
.pb{flex:1;overflow-y:auto;padding:16px}
.hint{color:var(--mute);margin:0 0 14px;font-size:14px}
.fld{display:block;margin-bottom:14px}
.fld span{display:block;font-size:14px;color:var(--soft);margin-bottom:5px;font-weight:500}
.fld input,.fld textarea{display:block;width:100%;border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:var(--card)}
.fld textarea{min-height:84px;resize:vertical}
.fld input:focus,.fld textarea:focus{border-color:var(--mute)}
.sheet{background:#fff;color:#1a1a1a;border-radius:6px;padding:34px 36px;font:15px/1.7 Georgia,"Times New Roman",serif;box-shadow:0 1px 8px rgba(0,0,0,.12)}
.sheet h3{font-size:18px;margin:0 0 16px;text-align:center}
.sheet h4{font-size:13px;margin:18px 0 4px}
.sheet p{margin:0 0 8px}
.v{font-style:italic;text-decoration:underline;text-decoration-color:#9aa0aa;text-underline-offset:3px}
.file{display:flex;align-items:center;gap:12px;border:1px solid var(--line);border-radius:14px;padding:12px;background:var(--card);max-width:440px}
.fi{width:40px;height:40px;border-radius:10px;background:var(--hover);display:grid;place-items:center;flex:none;color:var(--accent)}
.fm{flex:1;min-width:0}
.ov{position:fixed;inset:0;background:rgba(0,0,0,.4);display:grid;place-items:center;z-index:50;padding:20px}
.dlg{background:var(--pop);color:var(--ink);border-radius:18px;max-width:420px;width:100%;padding:22px;box-shadow:0 12px 50px rgba(0,0,0,.25)}
.dlg h2{font:500 21px Georgia,serif;margin:0 0 8px}
.dlg p{margin:0 0 12px;color:var(--soft)}
.dlg textarea{display:block;width:100%;border:1px solid var(--bd2);border-radius:10px;padding:10px;min-height:96px;background:var(--card)}
.link{background:var(--bubble);border-radius:10px;padding:9px 12px;font-size:13px;word-break:break-all}
.row{display:flex;justify-content:flex-end;gap:8px;margin-top:16px}
.toast{position:fixed;left:50%;bottom:96px;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:9px 16px;border-radius:10px;z-index:60;font-size:14px}
.auth{height:100%;overflow-y:auto;display:flex;flex-direction:column;background:var(--bg)}
.ahead{padding:22px 32px;font:600 24px Georgia,serif;color:var(--accent)}
.amain{flex:1;display:grid;grid-template-columns:1.1fr 1fr;align-items:center;gap:48px;max-width:1080px;width:100%;margin:0 auto;padding:12px 32px 48px}
.apitch h1{font:500 46px/1.12 Georgia,serif;margin:0 0 16px;letter-spacing:-.5px}
.apitch p{font-size:18px;color:var(--soft);max-width:28em;margin:0 0 20px}
.apitch ul{list-style:none;margin:0;padding:0;display:grid;gap:8px;color:var(--soft)}
.apitch li::before{content:"\\2713";color:var(--accent);font-weight:700;margin-right:10px}
.acard{border:1px solid var(--line);border-radius:20px;padding:28px;background:var(--card);box-shadow:0 8px 40px rgba(20,24,35,.07);max-width:420px;width:100%;justify-self:center}
.atabs{display:flex;padding:4px;background:var(--hover);border-radius:12px;margin-bottom:20px}
.atab{flex:1;padding:8px;border-radius:9px;color:var(--mute);font-weight:500}
.atab.on{background:var(--card);color:var(--ink);box-shadow:0 1px 3px rgba(0,0,0,.1)}
.af label{display:block;margin-bottom:14px}
.af label span{display:block;font-size:14px;color:var(--soft);margin-bottom:5px;font-weight:500}
.af input{display:block;width:100%;border:1px solid var(--bd2);border-radius:12px;padding:12px 14px;background:var(--card)}
.af input:focus{border-color:var(--mute)}
.aerr{color:#b42318;font-size:14px;min-height:20px;margin:0 0 8px}
.abtn{width:100%;padding:12px;border-radius:12px;background:var(--accent);color:#fff;font-weight:600}
.aswap{text-align:center;color:var(--mute);margin:16px 0 0;font-size:14px}
.aswap button{color:var(--accent);font-weight:600}
@media(max-width:900px){.panel{position:fixed;inset:0;width:100%;max-width:none;min-width:0;z-index:30}.tg{grid-template-columns:1fr 1fr}}
@media(max-width:820px){.amain{grid-template-columns:1fr;gap:28px;padding:8px 20px 40px}.apitch h1{font-size:34px}.ahead{padding:18px 20px}}
@media(max-width:760px){.side{position:fixed;z-index:20;inset:0 auto 0 0;margin-left:-290px;width:268px}.side.open{margin-left:0;box-shadow:0 0 40px rgba(0,0,0,.18)}.top{display:flex}.hero h1{font-size:26px}.ideas{grid-template-columns:1fr}}
@media(max-width:560px){.tg{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){.cv *{animation:none!important;transition:none!important}}
`;

/* ------------------------------ mic hook ------------------------------- */

function useMic(onText, notify) {
  const [on, setOn] = useState(false);
  const [text, setText] = useState("");
  const bars = useRef([]);
  const r = useRef({ heard: "" });

  const stop = (keep) => {
    const s = r.current;
    cancelAnimationFrame(s.raf);
    if (s.rec) { try { s.rec.stop(); } catch (e) { /* ignore */ } }
    if (s.stream) s.stream.getTracks().forEach((t) => t.stop());
    if (s.ac) { try { s.ac.close(); } catch (e) { /* ignore */ } }
    if (keep && s.heard) onText(s.heard);
    r.current = { heard: "" };
    setText("");
    setOn(false);
  };

  const start = async () => {
    if (!navigator.mediaDevices?.getUserMedia) return notify("Microphone is not supported in this browser");
    let stream;
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch (e) { return notify("Microphone access was blocked. Allow it in your browser settings."); }
    const ac = new (window.AudioContext || window.webkitAudioContext)();
    if (ac.resume) ac.resume();
    const an = ac.createAnalyser();
    an.fftSize = 64;
    ac.createMediaStreamSource(stream).connect(an);
    const d = new Uint8Array(an.frequencyBinCount);
    const s = { heard: "", stream, ac };
    const loop = (t) => {
      an.getByteFrequencyData(d);
      bars.current.forEach((b, i) => {
        if (b) b.style.transform = `scaleY(${Math.min(1, 0.14 + (d[i % d.length] / 255) * 0.9 + 0.08 * Math.abs(Math.sin(t / 180 + i)))})`;
      });
      s.raf = requestAnimationFrame(loop);
    };
    s.raf = requestAnimationFrame(loop);
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SR) {
      try {
        const rec = new SR();
        rec.continuous = true;
        rec.interimResults = true;
        rec.onresult = (e) => {
          let x = "";
          for (let i = 0; i < e.results.length; i++) x += e.results[i][0].transcript;
          s.heard = x;
          setText(x);
        };
        rec.onerror = () => {};
        rec.start();
        s.rec = rec;
      } catch (e) { /* ignore */ }
    }
    r.current = s;
    setOn(true);
  };

  useEffect(() => () => stop(false), []); // eslint-disable-line react-hooks/exhaustive-deps
  return { on, text, bars, start, stop };
}

/* ------------------------------ auth screen ---------------------------- */

function Auth({ onAuth }) {
  const [m, setM] = useState("login");
  const [f, setF] = useState({ name: "", email: "", pw: "" });
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    const email = f.email.trim().toLowerCase();
    if (m === "signup" && !f.name.trim()) return setErr("Enter your full name.");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setErr("Enter a valid email address.");
    if (f.pw.length < 8) return setErr("Use a password of at least 8 characters.");
    const h = await hashPw(f.pw);
    if (m === "signup") {
      if (ACCOUNTS[email]) return setErr("An account with this email already exists. Log in instead.");
      ACCOUNTS[email] = { name: f.name.trim(), h };
      store.set("civis-accounts", ACCOUNTS);
    } else if (!ACCOUNTS[email]) {
      return setErr("No account found for this email. Choose Sign up to create one.");
    } else if (ACCOUNTS[email].h !== h) {
      return setErr("Email or password is incorrect.");
    }
    store.set("civis-session", email);
    onAuth({ email, name: ACCOUNTS[email].name });
  };

  return (
    <div className="auth">
      <div className="ahead">Civis</div>
      <div className="amain">
        <div className="apitch">
          <h1>Legal help in plain language</h1>
          <p>Ask legal questions and draft contracts, letters and notices in minutes.</p>
          <ul><li>Clear answers you can act on</li><li>Ready-made templates for every document</li><li>Download your draft as a Word file</li></ul>
        </div>
        <div className="acard">
          <div className="atabs">
            <button type="button" className={"atab" + (m === "login" ? " on" : "")} onClick={() => { setM("login"); setErr(""); }}>Log in</button>
            <button type="button" className={"atab" + (m === "signup" ? " on" : "")} onClick={() => { setM("signup"); setErr(""); }}>Sign up</button>
          </div>
          <div className="af" onKeyDown={(e) => { if (e.key === "Enter" && e.target.tagName === "INPUT") submit(e); }}>
            {m === "signup" && <label><span>Full name</span><input value={f.name} onChange={set("name")} autoComplete="name" /></label>}
            <label><span>Email</span><input type="email" value={f.email} onChange={set("email")} autoComplete="email" /></label>
            <label><span>Password</span><input type="password" value={f.pw} onChange={set("pw")} autoComplete={m === "signup" ? "new-password" : "current-password"} /></label>
            <p className="aerr" role="alert">{err}</p>
            <button className="abtn" type="button" onClick={submit}>{m === "signup" ? "Create account" : "Log in"}</button>
          </div>
          <p className="aswap">
            {m === "signup" ? "Already have an account? " : "New to Civis? "}
            <button type="button" onClick={() => { setM(m === "signup" ? "login" : "signup"); setErr(""); }}>{m === "signup" ? "Log in" : "Create an account"}</button>
          </p>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------ template page -------------------------- */

function Templates({ onPick }) {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [all, setAll] = useState(false);
  const total = useMemo(() => Object.values(TPL).reduce((s, a) => s + a.length, 0), []);

  const list = useMemo(() => {
    if (!cat && !q) return [];
    const out = [];
    Object.keys(TPL).forEach((c) => TPL[c].forEach((n) => out.push([n, c])));
    const rank = (n) => (POP.includes(n) ? POP.indexOf(n) : 99);
    out.sort((a, b) => rank(a[0]) - rank(b[0]));
    const r = out.filter((x) => (!cat || x[1] === cat) && x[0].toLowerCase().includes(q.toLowerCase()));
    if (cat) r.sort((a, b) => a[0].localeCompare(b[0]));
    return r;
  }, [q, cat]);
  const shown = all ? list : list.slice(0, 9);

  return (
    <div className="tpl">
      <div className="ts"><Icon n="search" /><input value={q} onChange={(e) => { setQ(e.target.value); setAll(false); }} placeholder={`Search ${total} templates\u2026`} autoComplete="off" /></div>
      <div className="chips">
        {Object.keys(TPL).map((c) => (
          <button key={c} className={"chip" + (c === cat ? " on" : "")} onClick={() => { setCat(c === cat ? "" : c); setAll(false); }}>
            {c} <em>{TPL[c].length}</em>
          </button>
        ))}
      </div>
      <div className="tg">
        {shown.map(([n, c]) => (
          <button key={n} className="tc" onClick={() => onPick(n)}>
            <Icon n="doc" /><span><b>{n}</b><i>{c}</i></span>
          </button>
        ))}
        {!list.length && <p className="none">{cat || q ? "No templates match your search." : "Choose a category to see its templates."}</p>}
        {list.length > 9 && !all && <button className="more" onClick={() => setAll(true)}>Show all {list.length}</button>}
      </div>
    </div>
  );
}

/* ------------------------------ doc panel ------------------------------ */

function Panel({ doc, setDoc, onGenerate, onClose }) {
  const K = KINDS[doc.kind];
  return (
    <aside className="panel">
      <div className="ph">
        <h2>{doc.name}</h2>
        <div className="seg">
          {["fields", "preview"].map((t) => (
            <button key={t} className={doc.tab === t ? "on" : ""} onClick={() => setDoc({ ...doc, tab: t })}>{t === "fields" ? "Fields" : "Preview"}</button>
          ))}
        </div>
        <button className="gen" onClick={onGenerate}>Generate</button>
        {doc.done && <button className="ic" aria-label="Download" onClick={() => downloadDoc(doc)}><Icon n="down" /></button>}
        <button className="ic" aria-label="Close" onClick={onClose}><Icon n="x" /></button>
      </div>
      <div className="pb">
        {doc.tab === "fields" ? (
          <>
            <p className="hint">Replace the examples with your details, then press Generate.</p>
            {K.f.map(([k, label]) => {
              const big = k === "det" || k === "rel";
              const common = {
                value: doc.vals[k] ?? "",
                onChange: (e) => setDoc({ ...doc, vals: { ...doc.vals, [k]: e.target.value } }),
                onFocus: (e) => { if (!doc.touched[k]) { doc.touched[k] = true; e.target.select(); } },
              };
              return (
                <label className="fld" key={k}>
                  <span>{label}</span>
                  {big ? <textarea {...common} /> : <input {...common} />}
                </label>
              );
            })}
          </>
        ) : (
          <div className="sheet">
            <h3>{doc.name.toUpperCase()}</h3>
            {K.b.map(([h, p], i) => (
              <div key={i}>{h && <h4>{h}</h4>}<p><Filled p={p} d={doc} /></p></div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

/* --------------------------------- shell ------------------------------- */

let nextId = 2;

function Shell({ user, dark, setDark, onLogout }) {
  const [chats, setChats] = useState([{ id: 1, title: "New chat", msgs: [], doc: null }]);
  const [cur, setCur] = useState(1);
  const [mode, setMode] = useState("research");
  const [left, setLeft] = useState(20);
  const [min, setMin] = useState(false);
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState(false);
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState("");
  const [busy, setBusy] = useState(false);
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);
  const taRef = useRef(null);

  const chat = chats.find((c) => c.id === cur);
  const tplView = mode === "drafting" && chat.msgs.length === 0;
  const doc = chat.doc && !chat.doc.closed ? chat.doc : null;

  const say = (t) => { setToast(t); setTimeout(() => setToast(""), 2300); };
  const upd = (id, fn) => setChats((cs) => cs.map((c) => (c.id === id ? fn(c) : c)));
  const setDoc = (d) => upd(cur, (c) => ({ ...c, doc: d }));
  const mic = useMic((t) => setInput((v) => (v ? v + " " : "") + t), say);

  useEffect(() => { scrollRef.current && (scrollRef.current.scrollTop = 1e9); }, [chat.msgs.length, busy, cur, mode]);
  useEffect(() => {
    if (!menu) return undefined;
    const h = () => setMenu(false);
    document.addEventListener("click", h);
    return () => document.removeEventListener("click", h);
  }, [menu]);
  useEffect(() => {
    const ta = taRef.current;
    if (ta) { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 160) + "px"; }
  }, [input]);

  const newChat = () => {
    const id = nextId++;
    setChats((cs) => [{ id, title: "New chat", msgs: [], doc: null }, ...cs]);
    setCur(id);
    setOpen(false);
  };
  const pickMode = (m) => {
    setMode(m);
    if (m === "drafting" && chat.msgs.length) newChat();
  };
  const showSub = () => setModal({ title: "Civis Pro", body: <p>Longer documents, contract review and priority answers for people who use Civis every day.</p>, actions: [{ label: "Not now" }, { label: "Upgrade", pri: true, fn: () => say("Payments are not connected yet") }] });

  const send = async () => {
    const t = input.trim();
    if (!t || busy) return;
    if (left <= 0) return showSub();
    const id = cur;
    upd(id, (c) => ({ ...c, title: c.msgs.length ? c.title : t.length > 34 ? t.slice(0, 34) + "\u2026" : t, msgs: [...c.msgs, { r: "u", t }] }));
    setInput("");
    setLeft((n) => n - 1); // SEAM: the server must own this count
    setBusy(true);
    const history = [...chat.msgs, { r: "u", t }].filter((m) => m.r === "u" || m.r === "a");
    try {
      const a = await askCivis({ mode, messages: history });
      upd(id, (c) => ({ ...c, msgs: [...c.msgs, { r: "a", t: a }] }));
    } catch (e) {
      upd(id, (c) => ({ ...c, msgs: [...c.msgs, { r: "a", t: "The assistant is unavailable. Try again." }] }));
    }
    setBusy(false);
  };

  const pickTemplate = (n) => {
    const kind = kindOf(n, catOf(n));
    const vals = {};
    KINDS[kind].f.forEach(([k, , ex]) => { vals[k] = ex; });
    upd(cur, (c) => ({
      ...c,
      title: n,
      doc: { name: n, kind, vals, tab: "fields", done: false, closed: false, touched: {} },
      msgs: [...c.msgs, { r: "u", t: "Draft a " + n }, { r: "t", t: `I found the ${n} template. The form on the right has an example in each field. Replace the examples with your own details, then press Generate.` }],
    }));
  };
  const generate = () => {
    upd(cur, (c) => ({
      ...c,
      doc: { ...c.doc, done: true, tab: "preview" },
      msgs: [...c.msgs, { r: "u", t: "Generate the draft" }, { r: "a", t: "Your draft is ready." }, { r: "f", t: c.doc.name }],
    }));
  };
  const openDoc = (tab) => upd(cur, (c) => ({ ...c, doc: { ...c.doc, closed: false, tab } }));

  const menuAct = {
    sub: showSub,
    inv: () => setModal({ title: "Invite friends", body: (<><p>Share this link with anyone who could use Civis.</p><div className="link">{window.location.href}</div></>), actions: [{ label: "Close" }, { label: "Copy link", pri: true, fn: () => { navigator.clipboard?.writeText(window.location.href).then(() => say("Link copied"), () => say("Copy the link above")); } }] }),
    fb: () => { let v = ""; setModal({ title: "Feedback & support", body: (<><p>Tell us what went wrong or what you would like Civis to do.</p><textarea placeholder="Write your message" onChange={(e) => { v = e.target.value; }} /></>), actions: [{ label: "Cancel" }, { label: "Send", pri: true, fn: () => { if (v.trim()) say("Thanks, your message was sent"); } }] }); },
    ins: () => setModal({ title: "Install app", body: <p>Open your browser menu and choose Install app or Add to Home Screen.</p>, actions: [{ label: "Got it", pri: true }] }),
    dark: () => setDark(!dark),
    pri: () => setModal({ title: "Privacy Policy", body: <p>Placeholder. Replace with your approved privacy policy.</p>, actions: [{ label: "Close", pri: true }] }),
    ter: () => setModal({ title: "Terms & Conditions", body: <p>Placeholder. Replace with your approved terms.</p>, actions: [{ label: "Close", pri: true }] }),
    x: () => window.open("https://twitter.com/intent/tweet?text=" + encodeURIComponent("I use Civis, an AI assistant for legal questions."), "_blank", "noopener"),
    out: () => setModal({ title: "Log out of Civis?", body: <p>You can log back in at any time.</p>, actions: [{ label: "Cancel" }, { label: "Log out", pri: true, fn: onLogout }] }),
  };
  const MENU = [
    ["sub", "gem", "Subscribe"], ["inv", "users", "Invite friends"], ["fb", "mail", "Feedback & support"], ["ins", "down", "Install app"],
    ["dark", "moon", dark ? "Light mode" : "Dark mode"], "-",
    ["pri", "shield", "Privacy Policy"], ["ter", "doc", "Terms & Conditions"], ["x", "share", "Share about Civis on X"], "-",
    ["out", "out", "Logout"],
  ];

  const Msg = ({ m }) => {
    if (m.r === "u") return <div className="msg u"><div className="b">{m.t}</div></div>;
    return (
      <div className="msg a">
        <div className="mk">C</div>
        <div className="b">
          {m.r === "f" ? (
            <div className="file">
              <div className="fi"><Icon n="doc" /></div>
              <div className="fm"><b>{slug(m.t)}.doc</b><i>Word document</i></div>
              <button className="btn" onClick={() => openDoc("preview")}>Open</button>
              <button className="ic" aria-label="Download" onClick={() => downloadDoc(chat.doc)}><Icon n="down" /></button>
            </div>
          ) : (<><p>{m.t}</p>{m.r === "t" && <button className="btn" onClick={() => openDoc("fields")}>Open form</button>}</>)}
        </div>
      </div>
    );
  };

  return (
    <div className="app">
      <aside className={"side" + (min ? " min" : "") + (open ? " open" : "")}>
        {min ? (
          <div className="rail">
            <button className="ic" aria-label="Open sidebar" onClick={() => setMin(false)}><Icon n="panelOpen" /></button>
            <button className="ic" aria-label="New chat" onClick={newChat}><Icon n="edit" /></button>
            <button className="ic" aria-label="Drafting" onClick={() => pickMode("drafting")}><Icon n="draft" /></button>
            <button className="ic" aria-label="Chat history" onClick={() => setMin(false)}><Icon n="clock" /></button>
          </div>
        ) : (
          <>
            <div className="brandrow">
              <div className="brand">Civis</div>
              <button className="ic" style={{ marginTop: -8 }} aria-label="Close sidebar" onClick={() => (window.innerWidth <= 760 ? setOpen(false) : setMin(true))}><Icon n="panelClose" /></button>
            </div>
            <button className="new" onClick={newChat}>＋ New chat</button>
            <div className="modes" role="group" aria-label="Mode">
              <button className={"mode" + (mode === "research" ? " on" : "")} aria-pressed={mode === "research"} onClick={() => pickMode("research")}><Icon n="book" />Research</button>
              <button className={"mode" + (mode === "drafting" ? " on" : "")} aria-pressed={mode === "drafting"} onClick={() => pickMode("drafting")}><Icon n="draft" />Drafting</button>
            </div>
            <div className="list">
              {chats.map((c) => (
                <button key={c.id} className={"chat" + (c.id === cur ? " on" : "")} onClick={() => { setCur(c.id); setOpen(false); }}>{c.title}</button>
              ))}
            </div>
            <div className="acct" onClick={(e) => e.stopPropagation()}>
              {menu && (
                <div className="pop" role="menu">
                  <div className="mail">{user.email}</div>
                  {MENU.map((it, i) => it === "-" ? <div className="sep" key={i} /> : (
                    <button key={it[0]} className="it" role="menuitem" onClick={() => { setMenu(false); menuAct[it[0]](); }}><Icon n={it[1]} />{it[2]}</button>
                  ))}
                </div>
              )}
              <button className="me" aria-haspopup="menu" onClick={() => setMenu(!menu)}>
                <div className="av">{(user.name || user.email).charAt(0).toUpperCase()}</div>
                <span className="who"><b>{user.email}</b><i>{left} of 20 free prompts left</i></span>
                <Icon n="up" />
              </button>
            </div>
          </>
        )}
      </aside>

      <main className="main">
        <div className="top">
          <button className="ic" aria-label="Open sidebar" onClick={() => setOpen(!open)}>☰</button>
          <strong style={{ fontFamily: "Georgia,serif", color: "var(--accent)" }}>Civis</strong>
        </div>
        <div className="scroll" ref={scrollRef} onClick={() => setOpen(false)}>
          <div className="wrap">
            {tplView ? <Templates onPick={pickTemplate} />
              : chat.msgs.length === 0 ? (
                <div className="hero">
                  <h1>What would you like to research?</h1>
                  <div className="ideas">{IDEAS.research.map((i) => <button key={i} className="idea" onClick={() => { setInput(i); taRef.current?.focus(); }}>{i}</button>)}</div>
                </div>
              ) : (
                <>
                  {chat.msgs.map((m, i) => <Msg key={i} m={m} />)}
                  {busy && <div className="msg a"><div className="mk">C</div><div className="b dots"><span /><span /><span /></div></div>}
                </>
              )}
          </div>
        </div>
        <div className="bar">
          <div className={"box" + (tplView ? " wide" : "")}>
            {mic.on ? (
              <div className="voice">
                <div className="vt">{mic.text || "Listening\u2026"}</div>
                <div className="vr">
                  <div className="wv">{Array.from({ length: 28 }, (_, i) => <i key={i} ref={(el) => { mic.bars.current[i] = el; }} />)}</div>
                  <button className="ic" aria-label="Cancel" onClick={() => mic.stop(false)}><Icon n="x" /></button>
                  <button className="send" aria-label="Use text" onClick={() => mic.stop(true)}>✓</button>
                </div>
              </div>
            ) : (
              <>
                <textarea ref={taRef} rows={1} value={input} onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                  placeholder={tplView ? "Describe the document you need, or pick a template above" : mode === "drafting" ? "Describe the document you need" : "Ask Civis a legal question"} />
                <div className="tools">
                  <button className="ic" aria-label="Voice input" onClick={() => mic.start()}><Icon n="mic" /></button>
                  <span className="sp" />
                  <button className="subl" onClick={showSub}><Icon n="info" />Subscribe</button>
                  <button className="send" aria-label="Send" disabled={!input.trim() || busy} onClick={send}>↑</button>
                </div>
              </>
            )}
          </div>
          <p className="note">Civis is AI and can make mistakes. It is not a substitute for a lawyer.</p>
        </div>
      </main>

      {doc && <Panel doc={doc} setDoc={setDoc} onGenerate={generate} onClose={() => upd(cur, (c) => ({ ...c, doc: { ...c.doc, closed: true } }))} />}

      {modal && (
        <div className="ov" onClick={(e) => e.target === e.currentTarget && setModal(null)}>
          <div className="dlg" role="dialog" aria-modal="true">
            <h2>{modal.title}</h2>
            {modal.body}
            <div className="row">
              {modal.actions.map((a) => <button key={a.label} className={"btn" + (a.pri ? " pri" : "")} onClick={() => { setModal(null); a.fn && a.fn(); }}>{a.label}</button>)}
            </div>
          </div>
        </div>
      )}
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}

/* ---------------------------------- app -------------------------------- */

export default function App() {
  const [user, setUser] = useState(null);
  const [dark, setDark] = useState(false);
  const [session, setSession] = useState(0);
  useEffect(() => {
    const s = store.get("civis-session", null);
    if (s && ACCOUNTS[s]) setUser({ email: s, name: ACCOUNTS[s].name });
  }, []);
  return (
    <div className={"cv" + (dark ? " dark" : "")}>
      <style>{CSS}</style>
      {user
        ? <Shell key={session} user={user} dark={dark} setDark={setDark} onLogout={() => { store.del("civis-session"); setUser(null); setSession((s) => s + 1); }} />
        : <Auth onAuth={setUser} />}
    </div>
  );
}
