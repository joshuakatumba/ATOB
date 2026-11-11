import { downloadDoc } from "../lib/doc.js";
import Icon from "./Icon.jsx";
function Panel({ doc, setDoc, onGenerate, onClose }) {
  return (
    <aside className="panel">
      <div className="ph">
        <h2>{doc.name}</h2>
        <div className="ph-acts">
          <div className="seg">
            {["fields", "preview"].map((t) => (
              <button key={t} type="button" className={doc.tab === t ? "on" : ""} onClick={() => setDoc({ ...doc, tab: t })}>{t === "fields" ? "Fields" : "Preview"}</button>
            ))}
          </div>
          <button className="gen" type="button" onClick={onGenerate}>Generate</button>
          {doc.done && <button className="ic" type="button" aria-label="Download" onClick={() => downloadDoc(doc)}><Icon n="down" /></button>}
          <button className="ic" type="button" aria-label="Close" onClick={onClose}><Icon n="x" /></button>
        </div>
      </div>
      <div className="pb">
        {doc.tab === "fields" ? (
          <>
            <p className="hint">Replace the examples with your details, then press Generate.</p>
            {doc.fields.map(({ key: k, label, example, max_length }) => {
              const big = k === "det" || k === "rel";
              const common = {
                value: doc.vals[k] ?? "",
                maxLength: max_length || undefined,
                onChange: (e) => setDoc({ ...doc, touched: { ...doc.touched, [k]: true }, vals: { ...doc.vals, [k]: e.target.value } }),
                onFocus: (e) => { if (!doc.touched?.[k] && example && doc.vals[k] === example) { doc.touched[k] = true; e.target.select(); } },
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
          <div className="sheet" dangerouslySetInnerHTML={{ __html: doc.html }} />
        )}
      </div>
    </aside>
  );
}

export default Panel;
