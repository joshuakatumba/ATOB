import { http, ApiError } from "./http.js";
const IDEAS = {
  research: ["What are my rights if I am dismissed without notice?", "Explain the main clauses in an NDA", "How long do I have to file a claim for unpaid wages?", "Trademark or copyright for my brand name?"],
};
/* SEAM: replace with POST /v1/conversations/{id}/messages (streaming). */
async function askCivis({ id, mode, content, attachmentIds = [], onEvent, signal }) {
  const response = await http(`/v1/conversations/${id}/messages`, { body: { content, mode, attachment_ids: attachmentIds }, stream: true, signal });
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "", done = false;
  try {
    while (true) {
      const chunk = await reader.read();
      buffer += decoder.decode(chunk.value, { stream: !chunk.done }).replace(/\r\n/g, "\n");
      let end;
      while ((end = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, end);
        buffer = buffer.slice(end + 2);
        const event = frame.split("\n").find((line) => line.startsWith("event:"))?.slice(6).trim();
        const data = frame.split("\n").filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trimStart()).join("\n");
        if (!event || !data) continue;
        const value = JSON.parse(data);
        if (event === "error") throw new ApiError(value.code, value.message);
        if (event === "done") done = true;
        onEvent(event, value);
      }
      if (chunk.done) break;
    }
    if (!done) throw new Error("The assistant is unavailable. Try again.");
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}

export { IDEAS, askCivis };
