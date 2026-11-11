# Data model

## Hosted Research citations (migration 0006)

`messages.citations` is non-null JSONB (default []), containing only source ID/title/URL/date/collection metadata.
It is saved atomically with completion of the owned assistant message and restored through owned history.
Failed or incomplete messages keep an empty citation list. Retrieved passage text is not persisted by this migration.


## Unfinished drafts (migration 0005)

`conversation_drafts` has one owner-scoped row per conversation: template_version_id,
AES-GCM encrypted_values, positive revision, nullable document_id and updated_at.
Foreign keys reference conversations, users, template_versions and documents; an owner index supports isolation.
Saves lock the owned conversation and compare the expected revision. Changed values/version increment the
revision and clear document_id. Generation locks and checks the saved revision and values before attaching
the immutable document. No auth tables or quota balances are modified by autosave.

## Implemented integration subset (migration 0004)

The table below describes the broader intended model. Current additions are deliberately smaller:
`templates(id,slug,title,category)` and immutable version records with fields/body JSON,
version, draft/approved status and is_fake; private `documents` reference owner, conversation,
version, AES-256-GCM encrypted values, storage key and filename; `messages.document_id` links
persisted file cards; `feedback_tickets` store owner, category, message and optional owned conversation.
Foreign keys and an owner/date document index are applied through migration 0004, not ad-hoc changes.
No auth-provider tables are modified. Shared catalog queries require an active authenticated owner;
private documents and conversations filter by owner. This migration passed up/down/up on civis_test.
API and browser generation/download acceptance now pass with the development fixtures.

All ids UUID. All tables have created_at; mutable tables have updated_at. Foreign keys everywhere. Ownership checks in every query. The auth provider's user id is stored as auth_user_id.

| Table | Key columns | Notes |
|---|---|---|
| users | id, auth_user_id (unique), email, name, plan_id, preferences (JSON), referral_code, deleted_at | Mirror created on first authenticated call. Email comes from the auth service, never edited locally. |
| consents | user_id, document, version, accepted_at | Append only. |
| conversations | id, user_id, title, mode, deleted_at | Index on user_id and updated_at. |
| messages | id, conversation_id, role, content, status (complete, incomplete, blocked), model, input_tokens, output_tokens, retrieval_trace_id | No update after complete except feedback. |
| citations | message_id, source_type (corpus or upload), chunk_id, upload_id, page, citation_text, source_url, as_at_date, verified | |
| message_feedback | message_id, user_id, rating, comment | Unique per user per message. |
| usage_ledger | id, user_id, kind (grant, spend, refund), amount, reason, request_id, refund_of, created_at | Append only. UNIQUE(request_id, kind); refund_of references the original spend. Owner approved 2026-11-07. Balance is the signed sum. |
| usage_balance | user_id, balance | Maintained atomically with the ledger in one transaction. |
| plans | id, name, price_ugx, prompts, duration_days | Defined by D6. |
| subscriptions | id, user_id, plan_id, status, starts_at, ends_at, provider, provider_ref | |
| payment_events | provider, provider_event_id (unique), payload, processed_at | Idempotency store. |
| templates | id, slug, category, title, kind, current_version_id | |
| template_versions | id, template_id, version, fields (JSON schema), body (structured clauses), reviewed_by, reviewed_at, status (draft, approved, retired) | Only approved versions are served. Codex must never mark a version approved. |
| documents | id, user_id, template_version_id, values (encrypted), storage_key, created_at, expires_at | Values may contain personal data. |
| uploads | id, user_id, conversation_id (nullable), filename, mime, size, sha256, storage_key, status, status_reason, page_count, ocr_used, quality_score, hidden_text_flag, expires_at, deleted_at | Owner filter on every query. |
| upload_pages | upload_id, page, text, confidence | Page-level text for citation and verification. |
| upload_chunks | id, upload_id, user_id, text, embedding, tsv | Only for documents above the context budget. Private namespace. Never joined with chunks. |
| upload_events | upload_id, from_state, to_state, reason, at | Audit trail. |
| corpus_documents | id, doc_type, title, citation, jurisdiction, source_url, licence, ingested_at, content_hash | |
| chunks | id, corpus_document_id, parent_id, text, context, embedding, tsv, citation, in_force, valid_from, valid_to, embed_model | HNSW index on embedding. GIN index on tsv. |
| feedback_tickets | id, user_id, category, message, conversation_id | |
| audit_log | actor, action, target, at | Account deletion, exports, template approvals, billing changes, upload deletions. |

## Quota operation (the only allowed way to spend a prompt)
A single database statement that decrements the balance only if it is above zero, and inserts the ledger row keyed by the unique (request_id, kind), in one transaction. If zero rows are updated, return quota_exhausted. Replaying the same request id and operation kind must not spend twice. Refunds insert a refund row and increment, keyed by the same request id and refund kind so they also cannot repeat. A refund references an owned spend and must match its amount. This uniqueness resolution was approved by the owner on 2026-11-07.

## Retention
Defaults pending D12 and D16. Soft-deleted conversations purged after 30 days. Generated Word files expire after 7 days. Uploads per D16. Logs contain no message or document text.
