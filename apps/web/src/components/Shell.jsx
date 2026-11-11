import { useEffect, useRef, useState } from "react";
import { http } from "../lib/http.js";
import { askCivis } from "../lib/api.js";
import useMic from "../hooks/useMic.js";
import Sidebar from "./Sidebar.jsx";
import ChatView from "./ChatView.jsx";
import Composer from "./Composer.jsx";
import Panel from "./DocPanel.jsx";
import SupportingPanel from "./SupportingPanel.jsx";
import Modal from "./Modal.jsx";
import DocumentLibrary from "./DocumentLibrary.jsx";

const emptyChat = { id: null, title: "New chat", mode: "research", msgs: [], doc: null };
const asDraft = (d) => ({ ...d, vals: d.values, tab: d.id ? "preview" : "fields", done: !!d.id, closed: false, touched: {} });
const fromConversation = (c) => {
  const msgs = [];
  for (const m of c.messages || []) {
    const item = {
      id: m.id,
      r: m.document_id ? "f" : m.role === "user" ? "u" : "a",
      t: m.content,
      document_id: m.document_id,
      status: m.status,
      citations: m.citations || [],
      created_at: m.created_at,
      input_tokens: m.input_tokens,
      output_tokens: m.output_tokens,
    };
    const prev = msgs[msgs.length - 1];
    if (item.r === "f" && prev && prev.r === "a" && !prev.document_id) {
      prev.document_id = item.document_id;
      prev.file_title = item.t;
    } else {
      msgs.push(item);
    }
  }
  return { ...c, title: c.title || (c.mode === "drafting" ? "New draft" : "New chat"), msgs, doc: null };
};

function Shell({ user, dark, setDark, onLogout }) {
  const [chats, setChats] = useState([emptyChat]);
  const [historyCursor, setHistoryCursor] = useState(null);
  const historyLoading = useRef(false);
  const creatingChat = useRef(false);
  const [cur, selectCur] = useState(null);
  const [mode, setMode] = useState("research");
  const [left, setLeft] = useState(user.prompts_left);
  const [min, setMin] = useState(false);
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState(false);
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState("");
  const [busy, setBusy] = useState(false);
  const [attachments, setAttachments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [recentUploads, setRecentUploads] = useState([]);
  const [supportState, setSupportState] = useState(null);
  const sending = useRef(false);
  const request = useRef(null);
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);
  const taRef = useRef(null);
  const draftCache = useRef(new Map());
  const draftQueue = useRef(new Map());
  const selectedChat = useRef(null);
  const alive = useRef(true);
  const loadingChat = useRef(0);
  const feedbackPending = useRef(new Set());
  const latestState = useRef(null);
  useEffect(() => { alive.current = true; return () => { alive.current = false; request.current?.abort(); }; }, []);

  const chat = chats.find((c) => c.id && c.id === cur) || { ...emptyChat, mode, title: mode === "drafting" ? "New draft" : "New chat" };
  const tplView = mode === "drafting" && chat.msgs.length === 0;
  const doc = chat.doc && !chat.doc.closed ? chat.doc : null;
  const activeSupportMsg = supportState
    ? chat.msgs.find((m) => (m.id && m.id === supportState.msg?.id) || m === supportState.msg) || supportState.msg
    : null;

  latestState.current = { id: cur, doc };

  const say = (t) => { setToast(t); setTimeout(() => setToast(""), 2300); };
  const upd = (id, fn) => setChats((cs) => cs.map((c) => (c.id === id ? fn(c) : c)));
  const sameVals = (a, b) => a && b && Object.keys(a).length === Object.keys(b).length && Object.keys(a).every((k) => (a[k] ?? "") === (b[k] ?? ""));
  const setDoc = (d) => {
    upd(cur, (c) => {
      const changed = !sameVals(d.vals, c.doc?.vals);
      return { ...c, doc: changed ? { ...d, id: null, done: false, readOnly: false } : d };
    });
    if (d.tab === "preview" && cur && !d.readOnly) {
      persistDraft(cur, d).catch((e) => say(e.message));
    }
  };
  const persistDraft = (id, snapshot) => {
    const task = (draftQueue.current.get(id) || Promise.resolve()).catch(() => { }).then(async () => {
      let previous = draftCache.current.get(id);
      if (previous?.slug === snapshot.slug && previous.version === snapshot.version && sameVals(previous.values, snapshot.vals)) return previous;
      let saved;
      try {
        saved = await http(`/v1/conversations/${id}/draft`, {
          method: "PATCH", body: {
            slug: snapshot.slug, version: snapshot.version, values: snapshot.vals, revision: previous?.revision ?? snapshot.revision ?? 0,
          }
        });
      } catch (err) {
        if (err?.status === 409) {
          const latest = await http(`/v1/conversations/${id}/draft`);
          saved = await http(`/v1/conversations/${id}/draft`, {
            method: "PATCH", body: {
              slug: snapshot.slug, version: snapshot.version, values: snapshot.vals, revision: latest?.revision || 0,
            }
          });
        } else throw err;
      }
      draftCache.current.set(id, saved);
      upd(id, (c) => c.doc?.slug === saved.slug && c.doc.version === saved.version ? {
        ...c, doc: {
          ...c.doc, revision: saved.revision, html: saved.html,
          ...(sameVals(c.doc.vals, snapshot.vals) ? { id: saved.id, done: !!saved.id } : {}),
        }
      } : c);
      return saved;
    });
    draftQueue.current.set(id, task);
    return task;
  };
  const flushDraft = async () => {
    const current = latestState.current;
    if (current?.id && current.doc && !current.doc.readOnly) await persistDraft(current.id, current.doc);
  };
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

  const loadChat = async (id, preferPreview = false) => {
    const c = fromConversation(await http(`/v1/conversations/${id}`));
    const draft = await http(`/v1/conversations/${id}/draft`);
    if (draft) {
      draftCache.current.set(id, draft);
      c.doc = { ...asDraft(draft), ...(preferPreview ? { tab: "preview" } : {}) };
      let markedFirst = false;
      c.msgs = c.msgs.map((m) => {
        if (!markedFirst && m.r === "a" && !m.document_id) {
          markedFirst = true;
          return { ...m, r: "t" };
        }
        return m;
      });
    } else {
      const lastFile = [...c.msgs].reverse().find((m) => m.document_id);
      if (lastFile) {
        const d = await http(`/v1/documents/${lastFile.document_id}`);
        c.doc = { ...asDraft(d), readOnly: true };
      }
    }
    setChats((cs) => cs.some((old) => old.id === c.id) ? cs.map((old) => old.id === c.id ? c : old) : [c, ...cs.filter((old) => old.id)]);
    if (selectedChat.current === c.id) { selectCur(c.id); setMode(c.mode); }
    return c;
  };
  const setCur = (id) => {
    setSupportState(null);
    const load = ++loadingChat.current;
    (async () => {
      await flushDraft();
      if (load !== loadingChat.current || !alive.current) return;
      selectedChat.current = id;
      await loadChat(id);
    })().catch((e) => { if (load === loadingChat.current) say(e.message); });
  };
  useEffect(() => {
    let live = true;
    (async () => {
      const page = await http("/v1/conversations?limit=30");
      if (!live) return;
      setHistoryCursor(page.next_cursor);
      const items = page.items;
      if (!items.length) return;
      setChats(items.map(fromConversation));
      if (selectedChat.current === null) {
        selectedChat.current = items[0].id;
        await loadChat(items[0].id);
      }
    })().catch((e) => say(e.message));
    return () => { live = false; };
  }, []);
  const loadMoreChats = async () => {
    if (!historyCursor || historyLoading.current) return;
    historyLoading.current = true;
    try {
      const page = await http(`/v1/conversations?limit=30&cursor=${encodeURIComponent(historyCursor)}`);
      setChats((items) => { const ids = new Set(items.map((c) => c.id)); return [...items, ...page.items.filter((c) => !ids.has(c.id)).map(fromConversation)]; });
      setHistoryCursor(page.next_cursor);
    } catch (error) { say(error.message); }
    finally { historyLoading.current = false; }
  };
  const newChat = async (requested = mode) => {
    if (creatingChat.current) return null;
    creatingChat.current = true;
    try {
      await flushDraft();
      setSupportState(null);
      const nextMode = typeof requested === "string" ? requested : mode;
      const c = fromConversation(await http("/v1/conversations", { body: { mode: nextMode } }));
      setChats((cs) => [c, ...cs.filter((old) => old.id)]);
      selectedChat.current = c.id;
      selectCur(c.id);
      setMode(nextMode);
      setOpen(false);
      return c.id;
    } catch (e) { say(e.message); return null; }
    finally { creatingChat.current = false; }
  };
  const draftValues = doc ? JSON.stringify(doc.vals) : "";
  useEffect(() => {
    if (!doc || doc.readOnly || !cur || busy) return;
    const timer = setTimeout(() => { persistDraft(cur, doc).catch((e) => say(e.message)); }, 350);
    return () => clearTimeout(timer);
  }, [cur, doc?.slug, doc?.version, draftValues, busy]);
  useEffect(() => {
    const protect = (e) => {
      const current = latestState.current;
      if (!current?.doc || current.doc.readOnly) return;
      const saved = draftCache.current.get(current.id);
      if (saved?.slug !== current.doc.slug || saved.version !== current.doc.version || JSON.stringify(saved.values) !== JSON.stringify(current.doc.vals)) {
        e.preventDefault(); e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", protect);
    return () => window.removeEventListener("beforeunload", protect);
  }, []);

  const switchMode = async (nextMode) => {
    if (sending.current) request.current?.abort();
    try { await flushDraft(); } catch { }
    setSupportState(null);
    setAttachments([]);
    selectedChat.current = null;
    selectCur(null);
    setMode(nextMode);
    setOpen(false);
  };

  const pickMode = (m) => {
    if (m === mode) return;
    if (m === "drafting") {
      setModal({
        title: "Turn on Drafting mode?",
        center: true,
        body: <p>Civis will help you draft contracts, agreements, wills, notices, pleadings, and court judgments.</p>,
        actions: [
          { label: "Cancel" },
          { label: "Turn on", pri: true, fn: () => { switchMode("drafting"); } },
        ],
      });
    } else {
      setModal({
        title: "Turn off Drafting mode?",
        center: true,
        body: <p>This chat will close and a new one will open in research mode.</p>,
        actions: [
          { label: "Cancel" },
          { label: "Turn off", pri: true, fn: () => { switchMode("research"); } },
        ],
      });
    }
  };

  const showSub = async () => {
    try {
      const catalog = await http("/v1/billing/plans");
      const plans = catalog.items || [];
      let chosen = plans.find((p) => p.name === "Pro")?.id || plans[0]?.id;
      setModal({
        title: "Civis Plans (UGX)",
        body: (
          <div>
            <p>Pay with MTN Mobile Money, Airtel Money or Card. Unused prompts roll over while your 30-day plan is active.</p>
            {plans.map((p) => (
              <label key={p.id} className="fld" style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
                <input type="radio" name="civis-plan" defaultChecked={p.id === chosen} onChange={() => { chosen = p.id; }} />
                <span><strong>Civis {p.name}</strong> — UGX {p.price_ugx.toLocaleString()} ({p.prompts} prompts / {p.duration_days} days)</span>
              </label>
            ))}
          </div>
        ),
        actions: [
          { label: "Not now" },
          {
            label: "Continue to payment", pri: true, fn: async () => {
              if (!chosen) return;
              try {
                const res = await http("/v1/billing/checkout", { body: { plan_id: chosen } });
                if (res.checkout_url) window.location.assign(res.checkout_url);
              } catch (error) { say(error.message); }
            }
          },
        ],
      });
    } catch (error) {
      say(error.message);
    }
  };
  const onUpload = async (file) => {
    if (file.size > 10 * 1024 * 1024) return say("Maximum upload size is 10 MB.");
    setUploading(true);
    try {
      const base64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || "").split(",")[1] || "");
        reader.onerror = () => reject(new Error("Could not read file."));
        reader.readAsDataURL(file);
      });
      const uploaded = await http("/v1/uploads", {
        body: { filename: file.name, content_type: file.type || "application/octet-stream", data_base64: base64, conversation_id: cur },
      });
      setAttachments((items) => [...items.filter((x) => x.id !== uploaded.id).slice(-4), uploaded]);
      setRecentUploads((items) => [uploaded, ...items.filter((x) => x.id !== uploaded.id)].slice(0, 20));
      if (uploaded.warnings?.length) say(uploaded.warnings[0]);
      else say(`Attached ${uploaded.filename} (${uploaded.page_count}p)`);
      taRef.current?.focus();
    } catch (error) { say(error.message); }
    finally { setUploading(false); }
  };
  const onAttachExisting = (docItem) => {
    setAttachments((items) => items.some((x) => x.id === docItem.id) ? items : [...items.slice(-4), docItem]);
    say(`Attached ${docItem.filename} (${docItem.page_count}p)`);
    taRef.current?.focus();
  };
  const onRemoveAttachment = (uploadId) => {
    setAttachments((items) => items.filter((item) => item.id !== uploadId));
  };

  const send = async () => {
    const raw = input.trim();
    const t = raw || (attachments.length > 0 ? `Summarize and explain the key points of ${attachments.map((a) => a.filename).join(", ")}.` : "");
    if (!t || busy || sending.current) return;
    if (mode === "drafting" && doc && /^(generate|generate\s+the\s+draft|generate\s+draft|create\s+document)$/i.test(t)) {
      setInput("");
      await generate();
      return;
    }
    if (left <= 0) return showSub();
    sending.current = true;
    request.current = new AbortController();
    setBusy(true);
    setInput("");
    const currentAttachments = attachments.map((item) => item.id);
    setAttachments([]);
    const id = cur || await newChat(mode);
    if (!id) { sending.current = false; setBusy(false); return; }
    if (mode === "drafting" && currentAttachments.length === 0) {
      try {
        await flushDraft();
        const hadMessages = chat.msgs.length > 0;
        const result = await http("/v1/drafting/prefill", { body: { description: t, conversation_id: id }, signal: request.current.signal });
        setLeft(result.prompts_left);
        if (result.draft) {
          draftCache.current.set(id, result.draft);
        }
        await loadChat(id, hadMessages);
      } catch (e) {
        if (request.current?.signal.aborted) return;
        setInput(t);
        if (e.code === "quota_exhausted") showSub(); else say(e.message);
      } finally { sending.current = false; setBusy(false); }
      return;
    }
    upd(id, (c) => ({ ...c, title: c.msgs.length ? c.title : t.length > 34 ? t.slice(0, 34) + "\u2026" : t, msgs: [...c.msgs, { r: "u", t }, { r: "a", t: "", streaming: true }] }));
    try {
      await askCivis({
        id, mode, content: t, attachmentIds: currentAttachments, signal: request.current.signal, onEvent: (event, data) => {
          if (event === "meta") {
            setLeft(data.prompts_left);
            upd(id, (c) => ({ ...c, msgs: c.msgs.map((m) => m.streaming ? { ...m, id: data.assistant_message_id } : m) }));
          }
          if (event === "citations") upd(id, (c) => ({ ...c, msgs: c.msgs.map((m) => m.streaming ? { ...m, citations: data } : m) }));
          if (event === "delta") upd(id, (c) => ({ ...c, msgs: c.msgs.map((m) => m.streaming ? { ...m, t: m.t + data.text } : m) }));
          if (event === "done") upd(id, (c) => ({ ...c, msgs: c.msgs.map((m) => m.streaming ? { ...m, input_tokens: data.input_tokens, output_tokens: data.output_tokens } : m) }));
        }
      });
    } catch (e) {
      if (request.current?.signal.aborted) return;
      setInput(t);
      if (e.code === "quota_exhausted") showSub(); else say(e.message);
    } finally {
      if (!alive.current) { sending.current = false; return; }
      try {
        await flushDraft();
        await loadChat(id);
        setLeft((await http("/v1/me")).prompts_left);
      } catch (e) { say(e.message); }
      sending.current = false;
      setBusy(false);
    }
  };

  const stop = () => request.current?.abort();
  const feedback = async (identifier, rating) => {
    if (feedbackPending.current.has(identifier)) return;
    feedbackPending.current.add(identifier);
    try {
      await http(`/v1/messages/${identifier}/feedback`, { body: { rating } });
      setChats((items) => items.map((item) => ({ ...item, msgs: item.msgs.map((m) => m.id === identifier ? { ...m, rating } : m) })));
    } catch (error) { say(error.message); }
    finally { feedbackPending.current.delete(identifier); }
  };
  const onCopy = (txt) => {
    if (!txt) return;
    navigator.clipboard?.writeText(txt).then(() => say("Copied to clipboard"), () => say("Could not copy text"));
  };
  const onOpenSupport = (msg, focusIdx = null) => {
    setSupportState((prev) => {
      const sameMsg = prev && ((prev.msg?.id && prev.msg.id === msg.id) || prev.msg === msg);
      if (sameMsg && focusIdx === null) return null;
      return { msg, focusIndex: focusIdx };
    });
  };
  const renameChat = async (item, newTitle) => {
    if (!newTitle.trim()) return;
    try {
      const saved = await http(`/v1/conversations/${item.id}`, { method: "PATCH", body: { title: newTitle.trim() } });
      upd(item.id, (c) => ({ ...c, title: saved.title }));
    } catch (error) {
      say(error.message);
    }
  };
  const deleteChat = async (item) => {
    try {
      if (sending.current && item.id === cur) return say("Stop the response first.");
      await http(`/v1/conversations/${item.id}`, { method: "DELETE" });
      draftCache.current.delete(item.id);
      draftQueue.current.delete(item.id);
      setChats((items) => items.filter((c) => c.id !== item.id));
      if (selectedChat.current === item.id) {
        selectedChat.current = null;
        selectCur(null);
      }
      say("Conversation deleted");
    } catch (error) {
      say(error.message);
    }
  };

  const pickTemplate = async (n, slug) => {
    if (busy) return;
    setBusy(true);
    try {
      const template = await http(`/v1/templates/${slug}`);
      const vals = Object.fromEntries(template.fields.map((f) => [f.key, f.example]));
      const id = cur || await newChat("drafting");
      if (!id) return;
      await persistDraft(id, { slug, version: template.version, vals });
      await loadChat(id);
    } catch (e) { say(e.message); } finally { setBusy(false); }
  };
  const generate = async () => {
    if (busy || !doc) return;
    if (doc.fields.some((f) => !(doc.vals[f.key] ?? "").trim())) {
      return say("Fill in every field before generating.");
    }
    setBusy(true);
    const id = cur;
    try {
      const saved = await persistDraft(id, doc);
      await http(`/v1/templates/${doc.slug}/render`, { body: { values: saved.values, format: "docx", conversation_id: id, version: saved.version, draft_revision: saved.revision } });
      await flushDraft();
      await loadChat(id);
    } catch (e) { say(e.message); } finally { setBusy(false); }
  };
  const openDoc = async (tab, identifier) => {
    try {
      setSupportState(null);
      if (identifier) {
        await flushDraft();
        const d = await http(`/v1/documents/${identifier}`);
        upd(cur, (c) => ({ ...c, doc: { ...asDraft(d), tab, readOnly: true } }));
      } else upd(cur, (c) => ({ ...c, doc: { ...c.doc, closed: false, tab } }));
    } catch (e) { say(e.message); }
  };
  const legal = async (document, title) => {
    try {
      const data = await http(`/v1/legal/${document}`);
      setModal({
        title,
        body: <div style={{ whiteSpace: "pre-wrap", maxHeight: "55vh", overflowY: "auto" }}>{data.text}</div>,
        actions: [
          { label: "Close" },
          {
            label: "Accept", pri: true, fn: async () => {
              try {
                await http("/v1/me/consents", { body: { document, version: data.version } });
                say(`${title} accepted`);
              } catch (e) { say(e.message); }
            }
          },
        ],
      });
    } catch (e) { say(e.message); }
  };

  const exportChat = async () => {
    if (!cur) return say("Choose a conversation first.");
    try {
      const conversation = await http(`/v1/conversations/${cur}`);
      const url = URL.createObjectURL(new Blob([JSON.stringify(conversation, null, 2)], { type: "application/json" }));
      const link = document.createElement("a"); link.href = url; link.download = "civis-conversation.json";
      document.body.appendChild(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { say(error.message); }
  };
  const openLibraryDocument = async (item) => {
    try {
      await flushDraft();
      setSupportState(null);
      const document = await http(`/v1/documents/${item.id}`);
      const id = item.conversation_id || cur || await newChat("drafting");
      if (!id) return;
      if (item.conversation_id) { selectedChat.current = id; await loadChat(id); }
      upd(id, (c) => ({ ...c, doc: { ...asDraft(document), tab: "preview", readOnly: true } }));
      setModal(null);
    } catch (error) { say(error.message); }
  };
  const exportAccount = async () => {
    try {
      const data = await http("/v1/me/export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const link = document.createElement("a"); link.href = url; link.download = "civis-account-data.json";
      document.body.appendChild(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { say(error.message); }
  };
  const deleteAccount = () => setModal({
    title: "Delete account?",
    body: <p>This permanently deletes your Civis account, conversations and documents.</p>,
    actions: [
      { label: "Cancel" },
      {
        label: "Delete account", pri: true, fn: async () => {
          try {
            await http("/v1/me", { method: "DELETE" });
            window.dispatchEvent(new Event("civis:unauthenticated"));
          } catch (error) { say(error.message); }
        }
      },
    ],
  });
  const menuAct = {
    docs: () => setModal({ title: "My documents", body: <DocumentLibrary onOpen={openLibraryDocument} />, actions: [{ label: "Close" }] }),
    export: exportChat,
    exportAcct: exportAccount,
    delAcct: deleteAccount,
    sub: showSub,
    inv: () => setModal({ title: "Invite friends", body: (<><p>Share this link with anyone who could use Civis.</p><div className="link">{window.location.href}</div></>), actions: [{ label: "Close" }, { label: "Copy link", pri: true, fn: () => { navigator.clipboard?.writeText(window.location.href).then(() => say("Link copied"), () => say("Copy the link above")); } }] }),
    fb: () => { let v = ""; setModal({ title: "Feedback & support", body: (<><p>Tell us what went wrong or what you would like Civis to do.</p><textarea placeholder="Write your message" onChange={(e) => { v = e.target.value; }} /></>), actions: [{ label: "Cancel" }, { label: "Send", pri: true, fn: async () => { if (v.trim()) { try { await http("/v1/feedback", { body: { category: "feedback", message: v.trim(), conversation_id: cur } }); say("Thanks, your message was sent"); } catch (e) { say(e.message); } } } }] }); },
    ins: () => setModal({ title: "Install app", body: <p>Open your browser menu and choose Install app or Add to Home Screen.</p>, actions: [{ label: "Got it", pri: true }] }),
    dark: () => setDark(!dark).catch((e) => say(e.message)),
    pri: () => legal("privacy", "Privacy Policy"),
    ter: () => legal("terms", "Terms & Conditions"),
    x: () => window.open("https://twitter.com/intent/tweet?text=" + encodeURIComponent("I use Civis, an AI assistant for legal questions."), "_blank", "noopener"),
    out: () => setModal({ title: "Log out of Civis?", body: <p>You can log back in at any time.</p>, actions: [{ label: "Cancel" }, { label: "Log out", pri: true, fn: () => onLogout().catch((e) => say(e.message)) }] }),
  };
  const MENU = [
    ["sub", "gem", "Subscribe"], ["inv", "users", "Invite friends"], ["fb", "mail", "Feedback & support"], ["ins", "down", "Install app"],
    ["dark", "moon", dark ? "Light mode" : "Dark mode"], ["more", "more", "More"], "-",
    ["pri", "shield", "Privacy Policy"], ["ter", "doc", "Terms & Conditions"], ["x", "share", "Share about Civis on X"], "-",
    ["out", "out", "Logout"],
  ];
  const MORE_MENU = [
    ["docs", "doc", "My documents"], ["export", "down", "Export conversation"], ["exportAcct", "down", "Export account data"], "-",
    ["delAcct", "x", "Delete account"],
  ];

  return (
    <div className="app">
      <Sidebar {...{ min, open, setMin, setOpen, newChat, pickMode, mode, chats, cur, setCur, menu, setMenu, user, left, MENU, MORE_MENU, menuAct, onRenameChat: renameChat, onDeleteChat: deleteChat, historyCursor, loadMoreChats }} />

      <ChatView
        {...{
          setOpen,
          open,
          scrollRef,
          tplView,
          pickTemplate,
          say,
          chat,
          mode,
          newChat,
          setInput,
          taRef,
          busy,
          openDoc,
          feedback,
          onCopy,
          onOpenSupport,
          supportMsgId: activeSupportMsg?.id || activeSupportMsg,
        }}
      >
        <Composer {...{ tplView, mic, taRef, input, setInput, send, mode, showSub, busy, stop, attachments, uploading, recentUploads, onUpload, onAttachExisting, onRemoveAttachment }} />
      </ChatView>

      {doc ? (
        <Panel doc={doc} setDoc={setDoc} onGenerate={generate} onClose={() => upd(cur, (c) => ({ ...c, doc: { ...c.doc, closed: true } }))} />
      ) : activeSupportMsg ? (
        <SupportingPanel msg={activeSupportMsg} focusIndex={supportState?.focusIndex} onClose={() => setSupportState(null)} />
      ) : null}

      {modal && <Modal modal={modal} setModal={setModal} />}
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}

export default Shell;
