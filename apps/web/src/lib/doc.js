const slug = (s) => s.replace(/[^A-Za-z0-9]+/g, "_");
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
function downloadDoc(d) {
  if (!d?.id) return;
  const a = document.createElement("a");
  a.href = `/v1/documents/${d.id}/download`;
  a.download = d.filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}
export { slug, esc, downloadDoc };
