> Current owner scope (2026-11-07): integrate the supplied React 18/plain JSX/Vite UI with existing FastAPI/SuperTokens services. Preserve markup, copy and CSS. The earlier Next.js rebuild and milestone ordering below are historical; current scope and evidence are tracked in STATUS.md.

## Current delivery boundaries

Existing React screens now call server auth, chat/quota/history, template, feedback, legal and theme routes.
Local API/browser acceptance and backend static checks pass; remote CI and production remain unverified.
See STATUS.md for the exact verified scope. Mic/install/share/invite/collapse retain the owner implementation.
Stop, thumbs, citations UI, verification/reset screens, deletion/export, uploads and payments are deferred.
No new UI elements, CSS or frontend dependencies are part of this integration.


# Frontend feature to backend map

Every visible feature appears here. If a frontend feature is missing from this table, it must not be built. If a row says NONE, the feature is client-only.

## Account and access
| Frontend feature | Backend | Endpoint or job | Notes |
|---|---|---|---|
| Landing page, Sign up | Auth service | Auth SDK routes (signup) | Collect name, email, password. Must show and record consent to Terms and Privacy (version id). |
| Landing page, Log in | Auth service | Auth SDK routes (signin) | Generic error on failure. Never reveal whether an email exists. |
| Email verification | Auth service plus transactional email | Auth SDK routes | Unverified users get zero prompts. This is the main anti-abuse control. |
| Password reset | Auth service plus email | Auth SDK routes | Frontend pages needed (not in the prototype). |
| Logout (menu, confirm) | Auth service | Auth SDK signout | Revokes the session server-side. |
| Account row (email, initial) | API | GET /v1/me | |
| "X of 20 free prompts left" | API | GET /v1/me, and SSE meta event | Server is the only source of the count. Never compute locally. |
| Theme toggle (Dark mode) | API | PATCH /v1/me | Stored in preferences. Client also caches for first paint. |
| Delete account (new, required) | API plus worker | DELETE /v1/me | Not in the prototype. Data protection requires it. Asynchronous purge job. |
| Export my data (new, required) | API plus worker | GET /v1/me/export | Same reason. |

## Chat
| Frontend feature | Backend | Endpoint or job | Notes |
|---|---|---|---|
| Chat list in sidebar | API | GET /v1/conversations | Cursor paging, newest first. |
| New chat | API | POST /v1/conversations | Created lazily on first message to avoid empty rows. |
| Open a chat | API | GET /v1/conversations/{id} | Returns messages and citations. |
| Chat title | API | Set from first user message by the server. PATCH to rename. | No extra model call in v1. Truncate first message. |
| Delete chat (new) | API | DELETE /v1/conversations/{id} | Soft delete, hard purge by worker after retention window. |
| Mode switch (Research / Drafting) | API | mode field on conversation and on message request | Mode selects system prompt and tools. |
| Send message and streaming reply | API | POST /v1/conversations/{id}/messages (SSE) | Events: meta, delta, citations, done, error. Client uses fetch streaming, not EventSource. |
| Stop generating (new) | API | Client aborts the request | Server must detect disconnect and cancel the upstream call. |
| Citations under answers (new) | API | citations event and stored on message | Each links to source with "law as at" date. |
| Thumbs up/down (new) | API | POST /v1/messages/{id}/feedback | Feeds the review queue. |
| Hero suggestions | NONE | Static copy per mode | |
| Disclaimer footer | NONE | Static copy | Text must be legally approved. |
| Error and limit states (new) | API | Error codes in API.md | Needs designs: out of prompts, rate limited, model unavailable, verification required. |

## Drafting
| Frontend feature | Backend | Endpoint or job | Notes |
|---|---|---|---|
| Template search | API | GET /v1/templates?q= | Postgres full-text on title and category. |
| Category chips with counts | API | GET /v1/templates/categories | Counts from the database. Never hard-coded. |
| Template grid, Show all | API | GET /v1/templates with limit and cursor | Initial page of 9, then the rest. |
| Click template, form panel | API | GET /v1/templates/{slug} | Returns field schema and version. |
| Prefilled example values | API | Part of the template definition | Examples are marked as examples and never saved as real values. |
| Preview tab | API | POST /v1/templates/{slug}/render with format html | Debounced 400 ms. Server is the only renderer so preview and Word file cannot differ. |
| Generate | API | POST /v1/templates/{slug}/render with format docx | Creates a document record. Free (D4). |
| File card, Open | API | GET /v1/documents/{id} | Returns HTML preview. |
| File card, Download | API | GET /v1/documents/{id}/download | Redirect to a short-lived signed URL. |
| "Describe the document you need" | API | POST /v1/drafting/prefill | Model picks a template and fills values. Counts as a prompt. Unknown values stay null. |
| Fields never invented | API | Prefill output validated against the template schema | Reject unknown fields. |

## Document uploads (Milestone 4b, blocked)
| Frontend feature | Backend | Endpoint or job | Notes |
|---|---|---|---|
| Attach (paperclip) in composer | API | POST /v1/uploads (returns signed URL), then POST /v1/uploads/{id}/complete | Direct to storage. Show size and type limits before picking. |
| Upload progress and status chip | API | GET /v1/uploads/{id} polled | States and reasons from DOCUMENT_UPLOADS.md section 2. |
| Attachment shown on a message | API | attachment_ids on the message request | Ownership checked server-side. |
| Page and excerpt citations | API | citations event with page numbers | Same verification rules, source is the upload. |
| Source viewer for the uploaded file | API | GET /v1/uploads/{id}/pages/{n} | Returns extracted text of that page, not the original file. |
| My uploads list | API | GET /v1/uploads | Name, pages, state, expiry date. |
| Delete upload | API plus worker | DELETE /v1/uploads/{id} | Purges file, text, chunks and embeddings. |
| Unsupported or unreadable messages | API | Error codes in API.md | Needs designs. |
| Key-terms summary card | API | Structured output stored on the message | Same verification rules. |

## Billing, growth, support
| Frontend feature | Backend | Endpoint or job | Notes |
|---|---|---|---|
| Subscribe (menu and composer) | API | GET /v1/billing/plans, POST /v1/billing/checkout | Redirect to the provider checkout. |
| Subscription status | API | GET /v1/billing/status, also in /v1/me | |
| Payment confirmation | API | POST /v1/webhooks/{provider} | Signature verified, idempotent, then grants entitlement. |
| Invite friends | NONE in v1 (D8) | Static link | Do not build a reward system without D8. |
| Feedback and support | API | POST /v1/feedback | Stored and emailed to support. |
| Privacy Policy, Terms | API | GET /v1/legal/{doc} | Versioned text supplied by the owner. |
| Share about Civis on X | NONE | Static link | |
| Install app | NONE | PWA manifest and service worker | Limited on iOS. No backend. |
| Sidebar collapse | NONE | Client state | |
| Microphone and waveform | NONE in v1 | Browser speech recognition | See RISKS.md R7. |

## M2 frontend changes (after M1 foundations)
Owner approved M1 foundations before the M2 rebuild on 2026-11-07; this resolves the original ordering conflict with BUILD_PLAN.md.
Rebuild as a Next.js app. Add: stop button, delete chat, feedback thumbs, citation display, all error states, email verification screen, password reset screens, delete-account and export in settings, consent checkbox on signup. Remove the prototype's localStorage auth and in-browser Word generation.
