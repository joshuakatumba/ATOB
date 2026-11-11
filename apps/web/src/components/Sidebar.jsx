import { useEffect, useState } from "react";
import Icon from "./Icon.jsx";

function Sidebar({ min, open, setMin, setOpen, newChat, pickMode, mode, chats, cur, setCur, menu, setMenu, user, left, MENU, MORE_MENU = [], menuAct, onRenameChat, onDeleteChat, historyCursor, loadMoreChats }) {
  const [chatMenuId, setChatMenuId] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState("");

  useEffect(() => {
    if (!chatMenuId) return undefined;
    const close = () => setChatMenuId(null);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [chatMenuId]);

  const modeChats = chats.filter((c) => c.id && c.mode === mode);
  const newLabel = mode === "drafting" ? "New draft" : "New chat";
  const visibleChats = modeChats.length ? modeChats : [{ id: null, title: newLabel, mode, msgs: [] }];

  const commitRename = (c) => {
    const trimmed = editTitle.trim();
    setEditingId(null);
    if (trimmed && trimmed !== c.title) {
      onRenameChat?.(c, trimmed);
    }
  };

  const showRail = min && !open;

  return (
    <>
      {open && <div className="side-backdrop" aria-hidden="true" onClick={() => setOpen(false)} />}
      <aside className={"side" + (showRail ? " min" : "") + (open ? " open" : "")}>
        {showRail ? (
          <div className="rail">
            <button className="ic" aria-label="Open sidebar" onClick={() => setMin(false)}><Icon n="panelOpen" /></button>
            <button className="ic" aria-label={newLabel} onClick={() => newChat(mode)}><Icon n="edit" /></button>
            <button className="ic" aria-label="Drafting" onClick={() => pickMode("drafting")}><Icon n="draft" /></button>
            <button className="ic" aria-label="Chat history" onClick={() => setMin(false)}><Icon n="clock" /></button>
          </div>
        ) : (
          <>
            <div className="brandrow">
              <div className="brand">Civis</div>
              <button className="ic" style={{ marginTop: -8 }} aria-label="Close sidebar" onClick={() => (window.innerWidth <= 760 ? setOpen(false) : setMin(true))}><Icon n="panelClose" /></button>
            </div>
            <button className="new" onClick={() => newChat(mode)}>＋ {newLabel}</button>
            <div className="modes" role="group" aria-label="Mode">
              <button className={"mode" + (mode === "research" ? " on" : "")} aria-pressed={mode === "research"} onClick={() => pickMode("research")}><Icon n="book" />Research</button>
              <button className={"mode" + (mode === "drafting" ? " on" : "")} aria-pressed={mode === "drafting"} onClick={() => pickMode("drafting")}><Icon n="draft" />Drafting</button>
            </div>
            <div className="list">
              {visibleChats.map((c) => (
                <div key={c.id || "empty"} className={"chat-row" + (c.id === cur ? " on" : "")}>
                  {editingId === c.id ? (
                    <input
                      className="chat-edit"
                      value={editTitle}
                      maxLength={200}
                      autoFocus
                      onFocus={(e) => e.target.select()}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onBlur={() => commitRename(c)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") { e.preventDefault(); commitRename(c); }
                        if (e.key === "Escape") { e.preventDefault(); setEditingId(null); }
                      }}
                    />
                  ) : (
                    <button
                      className={"chat" + (c.id === cur ? " on" : "")}
                      style={{ flex: 1, minWidth: 0 }}
                      onClick={() => { if (c.id) setCur(c.id); setOpen(false); }}
                    >
                      {c.title}
                    </button>
                  )}
                  {c.id && (
                    <div className="chat-act-wrap" onClick={(e) => e.stopPropagation()}>
                      <button
                        className="ic chat-dots"
                        type="button"
                        aria-label={`Options for ${c.title}`}
                        onClick={() => setChatMenuId((prev) => (prev === c.id ? null : c.id))}
                      >
                        ⋯
                      </button>
                      {chatMenuId === c.id && (
                        <div className="chat-pop" role="menu">
                          <button
                            type="button"
                            className="it"
                            role="menuitem"
                            onClick={() => {
                              setChatMenuId(null);
                              setEditTitle(c.title || "");
                              setEditingId(c.id);
                            }}
                          >
                            <Icon n="edit" />
                            <span>Rename</span>
                          </button>
                          <button
                            type="button"
                            className="it danger"
                            role="menuitem"
                            onClick={() => {
                              setChatMenuId(null);
                              onDeleteChat?.(c);
                            }}
                          >
                            <Icon n="trash" />
                            <span>Delete</span>
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              {historyCursor && <button className="more" type="button" onClick={loadMoreChats}>Load more chats</button>}
            </div>
            <div className="acct" onClick={(e) => e.stopPropagation()}>
              {menu && (
                <div className="pop" role="menu">
                  {menu === "more" ? (
                    <>
                      <button type="button" className="it" onClick={() => setMenu(true)} style={{ fontWeight: 600, color: "var(--mute)" }}>← More</button>
                      <div className="sep" />
                      {MORE_MENU.map((it, i) => it === "-" ? <div className="sep" key={i} /> : (
                        <button key={it[0]} className="it" role="menuitem" onClick={() => { setMenu(false); menuAct[it[0]](); }}><Icon n={it[1]} />{it[2]}</button>
                      ))}
                    </>
                  ) : (
                    <>
                      <div className="mail">{user.email}</div>
                      {MENU.map((it, i) => it === "-" ? <div className="sep" key={i} /> : (
                        <button key={it[0]} className="it" role="menuitem" onClick={() => { if (it[0] === "more") setMenu("more"); else { setMenu(false); menuAct[it[0]](); } }}>
                          <Icon n={it[1]} />
                          <span style={{ flex: 1 }}>{it[2]}</span>
                          {it[0] === "more" && <span style={{ color: "var(--mute)" }}>›</span>}
                        </button>
                      ))}
                    </>
                  )}
                </div>
              )}
              <button className="me" aria-haspopup="menu" onClick={() => setMenu(menu ? false : true)}>
                <div className="av">{(user.name || user.email).charAt(0).toUpperCase()}</div>
                <span className="who"><b>{user.email}</b><i>{left} of 20 free prompts left</i></span>
                <Icon n="up" />
              </button>
            </div>
          </>
        )}
      </aside>
    </>
  );
}

export default Sidebar;
