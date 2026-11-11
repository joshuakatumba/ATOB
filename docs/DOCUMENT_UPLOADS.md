# User document uploads

Applies to documents users upload for analysis. Not the legal corpus (see RAG_AND_GUARDRAILS.md). Blocks on D14 to D17 and on Milestone 3 being complete.
Uploaded documents are never learned by the model. Text is extracted and placed in context for that conversation only. Nothing is fine-tuned or added to the shared corpus.

## 1. Scope for v1
- Supported: text-based PDF, DOCX within D14 limits.
- Image files and scanned PDFs: not supported until the OCR evaluation in section 6 passes. Reject with a clear message.
- Rejected outright: executables, archives, macro-enabled files, legacy .doc, password-protected or corrupt PDFs, files whose content does not match the declared type.
- Allowed actions: summarise, explain a clause, extract key terms (parties, dates, amounts, obligations, termination), list clauses that deserve an advocate's attention, answer questions about the document.
- Not allowed: declaring a document valid, enforceable, safe to sign, or complete. The answer must state what it did not check.
- Uploads are never visible to other users.

## 2. Processing states
uploaded, scanning, extracting, ready, failed, rejected. Each transition is recorded with a reason code. The frontend shows state and a human-readable reason on failure.

## 3. Pipeline (workers only, never in the request path)
1. Client uploads directly to private object storage using a short-lived signed URL with enforced size and content-type limits. The API never proxies file bytes.
2. Client calls complete. The API verifies the object exists, records its hash and moves state to scanning.
3. Validate the real file type from content, not the extension or declared type.
4. Malware scan. Infected files are deleted and the upload is rejected. Confirm scanner availability in the chosen host during Milestone 0. If unavailable, uploads stay disabled.
5. Extract text and structure: page boundaries, headings, numbered clauses, tables as text. DOCX is parsed from its XML. Embedded images are ignored in v1.
6. Quality check: extracted characters per page, proportion of non-text symbols, language detection. Below threshold, fail with "we could not read this reliably". Never continue with poor text.
7. Hidden-text check: flag invisible or tiny text. Flagged uploads are marked and the user is warned.
8. Store page-level text in the database with page numbers. Store the original file encrypted in object storage.
9. Documents under the token budget go into the model's context whole. Larger documents (only if D14 permits) are chunked, embedded in a private per-user namespace, and retrieved with the same hybrid pipeline. Never mix these chunks with corpus chunks, and always filter by owner inside the query.
10. Deduplicate by hash within one user only, never across users.

## 4. Using a document in chat
- The user attaches ready uploads to a message via attachment_ids. The server checks ownership.
- The prompt wraps the document text as untrusted data and labels each page. Instructions inside documents are ignored.
- During document analysis the model has no tools with side effects.
- Output is structured like corpus answers: each statement lists the page and clause it relies on.
- Verification: quoted text must be an exact substring of the extracted text of the cited page. Statements that cannot be tied to a page are removed. The citation shows page number and excerpt and opens the source viewer.
- Every analysis ends with the owner-approved caution text and a list of what was not checked.
- Answers combining a user document with law use both sources and label which is which. Law citations follow the full corpus verification rules.

## 5. Limits, cost and quota
- Per-user storage cap, upload count per day and token budget per document, all configurable (D14).
- Estimate tokens before analysis. If over budget, refuse with the reason instead of truncating silently.
- Quota cost of a document question per D15. Extraction and the upload list are free.
- One concurrent analysis per user.

## 6. OCR (blocked until evaluated)
- Benchmark candidate OCR engines on at least 100 real documents from Ugandan users, including phone photos, with preprocessing (rotate, deskew, contrast). Report character and clause-level accuracy in evals/.
- Enable image and scanned-PDF support only if the owner accepts the measured accuracy. Otherwise keep it disabled.
- OCR text is always marked as lower confidence in the UI.

## 7. Privacy and retention (pending D12, D16, D17)
- Originals and extracted text expire per D16. Deleting a conversation or an upload deletes the file, text, chunks and embeddings, and the purge is tested.
- Uploaded text is never written to logs or traces. Traces store ids and token counts only.
- Detect likely ID documents and bank statements and warn before analysis, per D17.
- Account deletion removes all uploads and derived data.

## 8. Failure behaviour
Extraction failure, scan failure, timeouts and model errors never consume a prompt. Worker retries are idempotent. Partial results are never shown.
