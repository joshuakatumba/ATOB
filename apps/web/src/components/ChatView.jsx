import { IDEAS } from "../lib/api.js";
import Icon from "./Icon.jsx";
import Templates from "./Templates.jsx";
import Msg from "./Message.jsx";
function AdvocateIllustration() {
  return (
    <svg className="hero-law" viewBox="0 0 120 120" fill="none" aria-hidden="true">
      <circle cx="60" cy="60" r="52" fill="var(--hover)" stroke="var(--line)" strokeWidth="1.5" />
      <circle cx="60" cy="36" r="11" fill="var(--accent)" />
      <path d="M47 28c3-5 8-7 13-7s10 2 13 7c-3-1.5-8-2.2-13-2.2S50 26.5 47 28z" fill="var(--ink)" opacity="0.22" />
      <path d="M35 86c0-15 11-26 25-26s25 11 25 26v6H35v-6z" fill="var(--accent)" />
      <path d="M54 59l6 13 6-13" fill="var(--card)" />
      <path d="M56.5 63v13l3.5-2 3.5 2V63" fill="var(--card)" stroke="var(--accent)" strokeWidth="1.2" />
      <rect x="40" y="72" width="22" height="16" rx="2.5" fill="var(--card)" stroke="var(--accent)" strokeWidth="1.8" />
      <path d="M44 77h14M44 81h10" stroke="var(--accent)" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M84 46v24M75 51h18" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
      <path d="M75 51l-3.5 8h7L75 51zM93 51l-3.5 8h7L93 51z" fill="var(--accent)" opacity="0.85" />
      <path d="M28 92h64" stroke="var(--accent)" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

function ChatView({ setOpen, open, scrollRef, tplView, pickTemplate, say, chat, mode, newChat, setInput, taRef, busy, openDoc, feedback, onCopy, onOpenSupport, supportMsgId, children }) {
  return (
      <main className="main">
        <div className="top">
          <button className="ic" type="button" aria-label="Open sidebar" onClick={() => setOpen(!open)}><Icon n="bars" /></button>
          <div className="top-title">
            <strong className="top-brand">Civis</strong>
            <span className="top-sub">{chat?.title || (mode === "drafting" ? "Drafting" : "Research")}</span>
          </div>
          {chat?.doc && (
            <button
              className="btn top-doc-btn"
              type="button"
              onClick={() => openDoc(chat.doc.tab || "fields")}
            >
              <Icon n="doc" />
              <span>{chat.doc.tab === "preview" ? "Preview" : "Form"}</span>
            </button>
          )}
          <button
            className="ic"
            type="button"
            aria-label={mode === "drafting" ? "New draft" : "New chat"}
            title={mode === "drafting" ? "New draft" : "New chat"}
            onClick={() => newChat?.(mode)}
          >
            <Icon n="plus" />
          </button>
        </div>
        <div className="scroll" ref={scrollRef} onClick={() => open && setOpen(false)}>
          <div className="wrap">
            {tplView ? <Templates onPick={pickTemplate} onError={say} />
              : chat.msgs.length === 0 ? (
                <div className="hero">
                  <AdvocateIllustration />
                  <h1>What would you like to research?</h1>
                  <div className="ideas">{IDEAS.research.map((i) => <button key={i} className="idea" onClick={() => { setInput(i); taRef.current?.focus(); }}>{i}</button>)}</div>
                </div>
              ) : (
                <>
                  {chat.msgs.map((m, i) => (
                    <Msg
                      key={i}
                      m={m}
                      hideMark={i > 0 && chat.msgs[i - 1].r !== "u"}
                      openDoc={openDoc}
                      chat={chat}
                      onFeedback={feedback}
                      onCopy={onCopy}
                      onOpenSupport={onOpenSupport}
                      supportActive={Boolean(supportMsgId && (m.id === supportMsgId || m === supportMsgId))}
                    />
                  ))}
                  {busy && !chat.msgs.some((m) => m.streaming && m.t) && <div className="msg a thinking"><div className="mk">C</div><div className="b dots"><span /><span /><span /></div></div>}
                </>
              )}
          </div>
        </div>
        {children}
      </main>
  );
}

export default ChatView;
