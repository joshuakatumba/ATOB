import { useEffect, useState } from "react";
import Icon from "./Icon.jsx";

function SearchModal({ open, onClose, chats, onSelect }) {
  const [query, setQuery] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIdx(0);
    }
  }, [open]);

  if (!open) return null;

  const q = query.trim().toLowerCase();
  const realChats = chats.filter(
    (c) => c.id && ((c.title && c.title !== "New chat" && c.title !== "New draft") || (c.msgs && c.msgs.length > 0))
  );
  const matches = q
    ? realChats.filter((c) => {
        const titleHit = (c.title || "").toLowerCase().includes(q);
        const msgHit = (c.msgs || []).some((m) => (m.t || "").toLowerCase().includes(q));
        return titleHit || msgHit;
      })
    : realChats.slice(0, 15);

  const clampedIdx = matches.length ? Math.min(activeIdx, matches.length - 1) : -1;

  const handleKeyDown = (e) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    } else if (e.key === "ArrowDown" && matches.length) {
      e.preventDefault();
      setActiveIdx((i) => (i + 1) % matches.length);
    } else if (e.key === "ArrowUp" && matches.length) {
      e.preventDefault();
      setActiveIdx((i) => (i - 1 + matches.length) % matches.length);
    } else if (e.key === "Enter" && clampedIdx >= 0 && matches[clampedIdx]) {
      e.preventDefault();
      onSelect(matches[clampedIdx].id);
      onClose();
    }
  };

  return (
    <div className="search-bg" onClick={onClose}>
      <div
        className="search-dlg"
        role="dialog"
        aria-modal="true"
        aria-label="Search chats"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="search-hd">
          <input
            type="text"
            value={query}
            autoFocus
            placeholder="Search..."
            aria-label="Search chats"
            onChange={(e) => {
              setQuery(e.target.value);
              setActiveIdx(0);
            }}
            onKeyDown={handleKeyDown}
          />
          <button type="button" className="ic search-x" aria-label="Close search" onClick={onClose}>
            <Icon n="x" />
          </button>
        </div>
        <div className="search-body">
          <div className="search-lbl">{q ? "Results" : "Recent chats"}</div>
          {matches.length === 0 ? (
            <p className="search-empty">{q ? "No matching chats found." : "No recent chats yet."}</p>
          ) : (
            <div className="search-list">
              {matches.map((c, idx) => (
                <button
                  key={c.id}
                  type="button"
                  className={"search-item" + (idx === clampedIdx ? " on" : "")}
                  onMouseEnter={() => setActiveIdx(idx)}
                  onClick={() => {
                    onSelect(c.id);
                    onClose();
                  }}
                >
                  <Icon n={c.mode === "drafting" ? "draft" : "chat"} />
                  <span className="search-item-title">{c.title}</span>
                  {c.mode === "drafting" && <span className="search-item-tag">Draft</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default SearchModal;

