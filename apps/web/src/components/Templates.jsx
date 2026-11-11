import { useEffect, useState } from "react";
import { http } from "../lib/http.js";
import Icon from "./Icon.jsx";
function Templates({ onPick, onError }) {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [all, setAll] = useState(false);
  const [categories, setCategories] = useState([]);
  const [total, setTotal] = useState(0);
  const [list, setList] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    http("/v1/templates/categories").then((page) => {
      if (live) { setCategories(page.items); setTotal(page.total); }
    }).catch((e) => { if (live) onError(e.message); });
    return () => { live = false; };
  }, []);
  useEffect(() => {
    let live = true;
    setLoading(true);
    const starterOnly = !cat && !q;
    const timer = setTimeout(async () => {
      try {
        let cursor = 0, items = [], page;
        do {
          page = await http(`/v1/templates?${new URLSearchParams({ q, category: cat, limit: starterOnly ? 6 : all ? 100 : 9, cursor })}`);
          items.push(...page.items);
          cursor = page.next_cursor;
        } while (!starterOnly && all && cursor !== null && live);
        if (live) {
          setList(items.map((item) => [item.title, item.category, item.slug]));
          setCount(starterOnly ? items.length : page.total);
        }
      } catch (e) { if (live) onError(e.message); }
      finally { if (live) setLoading(false); }
    }, starterOnly ? 0 : 200);
    return () => { live = false; clearTimeout(timer); };
  }, [q, cat, all]);
  const shown = list;

  return (
    <div className="tpl">
      <div className="ts"><Icon n="search" /><input value={q} onChange={(e) => { setQ(e.target.value); setAll(false); }} placeholder={`Search ${total} templates\u2026`} autoComplete="off" /></div>
      <div className="chips">
        {categories.map(({ name: c, count }) => (
          <button key={c} className={"chip" + (c === cat ? " on" : "")} onClick={() => { setCat(c === cat ? "" : c); setAll(false); }}>
            {c} <em>{count}</em>
          </button>
        ))}
      </div>
      <div className="tg">
        {shown.map(([n, c, slug]) => (
          <button key={n} className="tc" onClick={() => onPick(n, slug)}>
            <Icon n="doc" /><span><b>{n}</b><i>{c}</i></span>
          </button>
        ))}
        {!list.length && (
          <p className="none" role={loading ? "status" : undefined}>
            {loading ? "Loading templates\u2026" : cat || q ? "No templates match your search." : "Choose a category to see its templates."}
          </p>
        )}
        {count > 9 && !all && <button className="more" onClick={() => setAll(true)}>Show all {count}</button>}
      </div>
    </div>
  );
}

export default Templates;
