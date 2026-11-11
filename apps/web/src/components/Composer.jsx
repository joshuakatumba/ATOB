import { useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";

function Composer({ tplView, mic, taRef, input, setInput, send, mode, showSub, busy, stop, attachments = [], uploading = false, recentUploads = [], onUpload, onAttachExisting, onRemoveAttachment }) {
  const fileRef = useRef(null);
  const [addMenu, setAddMenu] = useState(false);
  const [drag, setDrag] = useState(false);

  useEffect(() => {
    if (!addMenu) return undefined;
    const close = () => setAddMenu(false);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [addMenu]);

  const handleFiles = async (fileList) => {
    if (!onUpload || !fileList?.length) return;
    for (const file of Array.from(fileList)) {
      await onUpload(file);
    }
  };

  const canSend = busy || Boolean(input.trim()) || attachments.length > 0;

  return (
    <div className="bar">
      <div
        className={"box" + (tplView ? " wide" : "") + (drag ? " drag" : "")}
        onDragOver={(e) => { if (onUpload) { e.preventDefault(); setDrag(true); } }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          if (!onUpload) return;
          e.preventDefault();
          setDrag(false);
          handleFiles(e.dataTransfer?.files);
        }}
      >
        {mic.on ? (
          <div className="voice">
            <div className="vt">{mic.text || "Listening\u2026 Speak now, then click \u2713"}</div>
            <div className="vr">
              <div className="wv">{Array.from({ length: 28 }, (_, i) => <i key={i} ref={(el) => { mic.bars.current[i] = el; }} />)}</div>
              <button className="ic" type="button" aria-label="Cancel" disabled={mic.busy} onClick={() => mic.stop(false)}><Icon n="x" /></button>
              <button className="send" type="button" aria-label="Transcribe audio" disabled={mic.busy} onClick={() => mic.stop(true)}>{mic.busy ? "\u2026" : "\u2713"}</button>
            </div>
          </div>
        ) : (
          <>
            {(attachments.length > 0 || uploading) && (
              <div className="cites">
                {attachments.map((att) => (
                  <span key={att.id} className="cite">
                    <Icon n="doc" />
                    <span className="cite-name">{att.filename}</span>
                    <em>({att.page_count}p)</em>
                    <button type="button" className="cite-rm" aria-label="Remove attachment" onClick={() => onRemoveAttachment?.(att.id)}>×</button>
                  </span>
                ))}
                {uploading && (
                  <span className="cite uploading">
                    <Icon n="doc" />
                    <span>Reading document\u2026</span>
                  </span>
                )}
              </div>
            )}
            <textarea
              ref={taRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder={
                attachments.length > 0
                  ? "Ask a question about your attached document (or press Enter to summarize)"
                  : tplView
                    ? "Describe the document you need, or pick a template above"
                    : mode === "drafting"
                      ? "Describe the document you need"
                      : "Ask Civis a legal question"
              }
            />
            <div className="tools">
              {onUpload && (
                <div className="add-wrap" onClick={(e) => e.stopPropagation()}>
                  <input
                    ref={fileRef}
                    type="file"
                    multiple
                    accept=".pdf,.docx,.txt,.md,.csv,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,text/csv"
                    hidden
                    onChange={(e) => {
                      const files = e.target.files;
                      setAddMenu(false);
                      handleFiles(files);
                      e.target.value = "";
                    }}
                  />
                  <button
                    className="ic"
                    type="button"
                    title="Attach document (PDF, Word, TXT)"
                    aria-label="Upload PDF or Word document"
                    onClick={() => setAddMenu((v) => !v)}
                  >
                    <Icon n="plus" />
                  </button>
                  {addMenu && (
                    <div className="add-pop" role="menu">
                      <div className="add-hd">Add Context</div>
                      <button
                        type="button"
                        className="it"
                        onClick={() => {
                          setAddMenu(false);
                          fileRef.current?.click();
                        }}
                      >
                        <Icon n="clip" />
                        <span>Files (PDF, Word, TXT)</span>
                      </button>
                      {recentUploads.filter((u) => !attachments.some((a) => a.id === u.id)).slice(0, 4).map((u) => (
                        <button
                          key={u.id}
                          type="button"
                          className="it"
                          onClick={() => {
                            setAddMenu(false);
                            onAttachExisting?.(u);
                          }}
                        >
                          <Icon n="doc" />
                          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {u.filename} ({u.page_count}p)
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
              <button className="ic" type="button" title="Voice input" aria-label="Voice input" onClick={() => mic.start()}><Icon n="mic" /></button>
              <span className="sp" />
              <button className="subl" type="button" onClick={showSub}><Icon n="info" />Subscribe</button>
              <button className="send" type="button" aria-label={busy ? "Stop response" : "Send"} disabled={!canSend} onClick={busy ? stop : send}>{busy ? "■" : "↑"}</button>
            </div>
          </>
        )}
      </div>
      <p className="note">Civis is AI and can make mistakes. It is not a substitute for a lawyer.</p>
    </div>
  );
}

export default Composer;
