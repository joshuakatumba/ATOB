import Icon from "./Icon.jsx";
import { slug, downloadDoc } from "../lib/doc.js";

function renderInline(text, m, onOpenSupport) {
  if (!text) return null;
  const cleaned = text.replace(/(\[\d+\](?:\s*[;,]?\s*\[\d+\])*)\s*\./g, "$1.");
  const tokenRe = /(\*\*[^*]+\*\*|\[\d+\](?:\s*[;,]?\s*\[\d+\])*)/g;
  const parts = cleaned.split(tokenRe);
  return parts.map((part, idx) => {
    if (!part) return null;
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>;
    }
    if (/^\[\d+\]/.test(part)) {
      const nums = [...part.matchAll(/\[(\d+)\]/g)].map((match) => Number(match[1]));
      return (
        <span key={idx} className="cbadges">
          {nums.map((n, j) => (
            <span key={j}>
              {j > 0 && <span className="csep"> ; </span>}
              <button
                type="button"
                className="cbadge"
                title={`View supporting source ${n}`}
                onClick={() => onOpenSupport?.(m, n - 1)}
              >
                {n}
              </button>
            </span>
          ))}
        </span>
      );
    }
    return part;
  });
}

function renderFormattedProse(text, m, onOpenSupport) {
  if (!text) return null;
  const blocks = text.split(/\n{2,}/).map((b) => b.trim()).filter(Boolean);
  return blocks.map((block, bIdx) => {
    const lines = block.split("\n").map((l) => l.trim()).filter(Boolean);
    if (!lines.length) return null;

    const numMatch = lines[0].match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      const num = numMatch[1];
      const firstRest = numMatch[2];
      let heading = "";
      let bodyLines = lines.slice(1);

      const boldSplit = firstRest.match(/^\*\*([^*]+)\*\*[:.\s-]*(.*)$/);
      if (boldSplit) {
        heading = boldSplit[1].trim();
        if (boldSplit[2].trim()) bodyLines = [boldSplit[2].trim(), ...bodyLines];
      } else if (bodyLines.length > 0 && firstRest.length < 110 && !/[.?!]$/.test(firstRest)) {
        heading = firstRest.replace(/^\*\*|\*\*$/g, "").trim();
      } else {
        const colonIdx = firstRest.indexOf(":");
        if (colonIdx > 2 && colonIdx < 85) {
          heading = firstRest.slice(0, colonIdx).replace(/^\*\*|\*\*$/g, "").trim();
          const afterColon = firstRest.slice(colonIdx + 1).trim();
          if (afterColon) bodyLines = [afterColon, ...bodyLines];
        }
      }

      const bulletLines = bodyLines.filter((l) => /^[-*•◦○]\s+/.test(l));
      const proseLines = bodyLines.filter((l) => !/^[-*•◦○]\s+/.test(l));

      return (
        <div key={bIdx} className="res-item">
          <div className="res-item-hd">
            <span className="res-num">{num}.</span>
            <div className="res-item-content">
              {heading ? (
                <>
                  <strong className="res-title">{renderInline(heading, m, onOpenSupport)}</strong>
                  {proseLines.length > 0 && (
                    <div className="res-sub">{renderInline(proseLines.join(" "), m, onOpenSupport)}</div>
                  )}
                </>
              ) : (
                <div className="res-sub">{renderInline([firstRest, ...proseLines].join(" "), m, onOpenSupport)}</div>
              )}
              {bulletLines.length > 0 && (
                <ul className="res-bullets">
                  {bulletLines.map((bl, lIdx) => (
                    <li key={lIdx}>{renderInline(bl.replace(/^[-*•◦○]\s+/, ""), m, onOpenSupport)}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      );
    }

    if (lines.every((l) => /^[-*•◦○]\s+/.test(l))) {
      return (
        <ul key={bIdx} className="res-bullets">
          {lines.map((bl, lIdx) => (
            <li key={lIdx}>{renderInline(bl.replace(/^[-*•◦○]\s+/, ""), m, onOpenSupport)}</li>
          ))}
        </ul>
      );
    }

    const bulletIdx = lines.findIndex((l) => /^[-*•◦○]\s+/.test(l));
    if (bulletIdx > 0) {
      const topProse = lines.slice(0, bulletIdx).join(" ");
      const subBullets = lines.slice(bulletIdx);
      return (
        <div key={bIdx} className="res-para-group">
          <p className="res-p">{renderInline(topProse, m, onOpenSupport)}</p>
          <ul className="res-bullets">
            {subBullets.map((bl, lIdx) => (
              <li key={lIdx}>{renderInline(bl.replace(/^[-*•◦○]\s+/, ""), m, onOpenSupport)}</li>
            ))}
          </ul>
        </div>
      );
    }

    return <p key={bIdx} className="res-p">{renderInline(lines.join(" "), m, onOpenSupport)}</p>;
  });
}

function formatStamp(createdAt) {
  try {
    const dt = createdAt ? new Date(createdAt) : new Date();
    if (Number.isNaN(dt.getTime())) return "";
    return dt.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

const Msg = ({ m, hideMark, openDoc, chat, onFeedback, onCopy, onOpenSupport, supportActive }) => {
  if (m.streaming && !m.t) return null;
  if (m.r === "u") return <div className="msg u"><div className="b">{m.t}</div></div>;
  const fileTitle = m.file_title || m.t;
  const fileCard = (m.r === "f" || m.document_id) && (
    <div className="file">
      <div className="fi"><Icon n="doc" /></div>
      <div className="fm"><b>{slug(fileTitle)}.docx</b><i>Word document</i></div>
      <button className="btn" onClick={() => openDoc("preview", m.document_id)}>Open</button>
      <button className="ic" aria-label="Download" onClick={() => downloadDoc({ id: m.document_id, filename: slug(fileTitle) + ".docx" })}><Icon n="down" /></button>
    </div>
  );

  const totalTokens = (Number(m.input_tokens) || 0) + (Number(m.output_tokens) || 0);
  const stamp = formatStamp(m.created_at);
  const showActions = m.r === "a" && Boolean(m.t);

  return (
    <div className="msg a">
      <div className="msg-col">
        <div className="msg-top">
          {hideMark ? <div className="mk" style={{ visibility: "hidden" }} aria-hidden="true">C</div> : <div className="mk">C</div>}
          <span className="sp" />
          {showActions && (
            <div className="msg-acts">
              <button
                type="button"
                className="msg-act"
                title="Copy response"
                aria-label="Copy response"
                onClick={() => onCopy?.(m.t)}
              >
                <Icon n="copy" />
              </button>
              <button
                type="button"
                className={"msg-act" + (supportActive ? " on" : "")}
                title="Show supporting content"
                aria-label="Show supporting content"
                onClick={() => onOpenSupport?.(m, null)}
              >
                <Icon n="support" />
              </button>
            </div>
          )}
        </div>
        <div className="b res-body">
          {m.r === "f" ? (
            fileCard
          ) : (
            <>
              <div className="res-prose">
                {m.t
                  ? renderFormattedProse(m.t, m, onOpenSupport)
                  : m.status === "incomplete"
                    ? <p className="res-p">Response unavailable.</p>
                    : null}
              </div>
              {fileCard}
              {m.r === "t" && <button className="btn" onClick={() => openDoc("fields")}>Open form</button>}
              {m.citations?.length > 0 && (
                <div className="refs-block">
                  <div className="refs-hd">References:</div>
                  <div className="refs-list">
                    {m.citations.map((c, i) => {
                      const label = `${i + 1}. ${c.title}${c.date && c.date !== "Uploaded document" ? ` (${c.date})` : ""}`;
                      return (
                        <button
                          key={c.id || c.url || i}
                          type="button"
                          className="ref-pill"
                          onClick={() => onOpenSupport?.(m, i)}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
              {m.t && !m.streaming && (
                <div className="msg-meta-row">
                  <span className="msg-meta">
                    {totalTokens > 0 ? `${totalTokens.toLocaleString()} tokens \u00b7 ` : ""}
                    {stamp}
                  </span>
                  {m.r === "a" && !m.document_id && m.id && m.status === "complete" && (
                    <div className="rate-row" aria-label="Rate response">
                      <button className="ic" type="button" aria-label="Helpful response" aria-pressed={m.rating === 1} onClick={() => onFeedback(m.id, 1)}>👍</button>
                      <button className="ic" type="button" aria-label="Unhelpful response" aria-pressed={m.rating === -1} onClick={() => onFeedback(m.id, -1)}>👎</button>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Msg;
