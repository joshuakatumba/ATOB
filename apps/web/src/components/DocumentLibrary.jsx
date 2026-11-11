import { useEffect, useState } from "react";
import { http } from "../lib/http.js";
import { downloadDoc } from "../lib/doc.js";

export default function DocumentLibrary({ onOpen }) {
  const [page, setPage] = useState({ items: [], next_cursor: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const request = new AbortController();
    http("/v1/documents?limit=30", { signal: request.signal }).then(setPage)
      .catch((e) => { if (!request.signal.aborted) setError(e.message); })
      .finally(() => { if (!request.signal.aborted) setLoading(false); });
    return () => request.abort();
  }, []);
  const more = async () => {
    if (loading || !page.next_cursor) return;
    setLoading(true); setError("");
    try {
      const next = await http(`/v1/documents?limit=30&cursor=${encodeURIComponent(page.next_cursor)}`);
      setPage((old) => ({ ...next, items: [...old.items, ...next.items] }));
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };
  const remove = async (id) => {
    setError("");
    try {
      await http(`/v1/documents/${id}`, { method: "DELETE" });
      setPage((old) => ({ ...old, items: old.items.filter((i) => i.id !== id) }));
    } catch (e) { setError(e.message); }
  };
  return <div>
    {error && <p role="alert">{error}</p>}
    {loading && <p role="status">Loading documents…</p>}
    {!loading && !page.items.length && !error && <p>No documents yet.</p>}
    {page.items.map((item) => <div className="file lib-file" key={item.id}>
      <div className="fm"><b>{item.name}</b><i>{new Date(item.created_at).toLocaleDateString()}</i></div>
      <div className="file-acts">
        <button className="btn" onClick={() => onOpen(item)}>Open</button>
        <button className="btn" onClick={() => downloadDoc(item)}>Download</button>
        <button className="btn" onClick={() => remove(item.id)}>Delete</button>
      </div>
    </div>)}
    {page.next_cursor && <button className="btn" disabled={loading} onClick={more}>Load more documents</button>}
  </div>;
}
