import { IDEAS } from "../lib/api.js";
import Icon from "./Icon.jsx";
import Templates from "./Templates.jsx";
import Msg from "./Message.jsx";
function ChatView({ setOpen, open, scrollRef, tplView, pickTemplate, say, chat, mode, newChat, setInput, taRef, busy, openDoc, feedback, onCopy, onOpenSupport, supportMsgId, children }) {
  return (
      <main className="main">
        <div className="top">
          <button className="ic" type="button" aria-label="Open sidebar" onClick={() => setOpen(!open)}>☰</button>
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
                  {busy && !chat.msgs.some((m) => m.streaming && m.t) && <div className="msg a"><div className="mk">C</div><div className="b dots"><span /><span /><span /></div></div>}
                </>
              )}
          </div>
        </div>
        {children}
      </main>
  );
}

export default ChatView;
