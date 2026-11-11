import { useEffect, useRef } from "react";
import Icon from "./Icon.jsx";

function SupportingPanel({ msg, focusIndex, onClose }) {
  const cardRefs = useRef([]);
  const citations = msg?.citations || [];

  useEffect(() => {
    if (focusIndex != null && cardRefs.current[focusIndex]) {
      cardRefs.current[focusIndex].scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [focusIndex, msg?.id]);

  return (
    <aside className="panel sup-panel" aria-label="Supporting Content">
      <div className="ph sup-ph">
        <div className="sup-tabs">
          <span className="sup-tab on"><Icon n="list" /></span>
          <span className="sup-tab"><Icon n="support" /></span>
        </div>
        <h2>Supporting Content</h2>
        <button className="ic" type="button" aria-label="Close supporting content" onClick={onClose}>
          <Icon n="x" />
        </button>
      </div>
      <div className="pb sup-body">
        {citations.length === 0 ? (
          <p className="hint">No supporting passages are attached to this response.</p>
        ) : (
          citations.map((c, idx) => {
            const isLocalUpload = !c.url || String(c.url).startsWith("#upload-");
            const headerText = `${c.title || "Legal Source"}${c.date && c.date !== "Uploaded document" ? ` (${c.date})` : ""}`;
            return (
              <div
                key={c.id || c.url || idx}
                ref={(el) => { cardRefs.current[idx] = el; }}
                className={"sup-card" + (focusIndex === idx ? " focus" : "")}
              >
                <div className="sup-card-hd">
                  {isLocalUpload ? (
                    <span className="sup-link">{headerText}</span>
                  ) : (
                    <a className="sup-link" href={c.url} target="_blank" rel="noopener noreferrer">
                      {headerText}
                    </a>
                  )}
                </div>
                <div className="sup-card-txt">
                  {c.text ? c.text : "Official statutory or case law authority from the Uganda Legal Information Institute (ULII). Click the title above to view the full source text."}
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}

export default SupportingPanel;

