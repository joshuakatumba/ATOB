# Core product testing

Owner scope, 2026-11-09: real Groq chat, existing counsel-approved testing templates, and existing per-conversation memory. No new frontend dependencies or redesign.

## Configure

Edit the existing private .env; do not replace database/storage credentials. Never commit it.

```dotenv
LLM_PROVIDER=groq
FAKE_MODEL=false
GROQ_API_KEY=YOUR_KEY
LLM_MODEL=openai/gpt-oss-120b
GROQ_REASONING_EFFORT=low
LLM_MAX_OUTPUT_TOKENS=2048
OWNER_TEMPLATES_FILE=content/owner-supplied/templates.json
ALLOW_UNAPPROVED_TEMPLATES=false
LLM_HISTORY_MAX_CHARS=24000
```

Key, model and provider are server environment settings; no key is in frontend code or repository content.
The owner-pasted key was configured privately for local testing; rotate it because it was shared in chat.
Groq model availability is account-dependent; this model was returned by the account's model-list API.

Start/update the app with `sudo ./scripts/dev.sh`. It builds API/web/worker and imports the 62 original templates unchanged.
For only a key change, edit .env and run `sudo docker compose up -d --force-recreate api worker`.

## Memory

All chat messages are saved in Postgres under their conversation/owner. Reloading restores them.
Each model request receives up to the newest 60 completed, non-file messages, bounded by LLM_HISTORY_MAX_CHARS.
Old messages remain stored even when outside that request budget. No automatic summarization, cross-chat profile memory or training is implemented.
Incomplete/blocked messages and file-card titles are not supplied as normal answer history.
Generated documents and unfinished forms reopen from the server. Form edits autosave after 350 ms;
switching chats and generating flush pending changes. Reloading before a save completes shows the browser's
unsaved-change prompt. Draft values are encrypted in Postgres, tied to owner/conversation and exact template version.
Stale saves return a conflict rather than overwriting a newer revision. Editing clears the active generated-file link.

## Templates

The template catalog is mechanically extracted from the owner-supplied Civis.jsx. Its wording, fields and category mapping are preserved.
Source hash and the owner's testing approval are recorded in content/owner-supplied/templates.json and content provenance.
The importer is idempotent. New drafts no longer hide the most recent approved version.
Owner approval is not applied to the separate FAKE seed corpus/legal records.

In Drafting, describe the document to select an approved template and prefill literal stated facts through
the configured model. Missing facts stay blank; low-confidence selection asks for more detail using existing UI copy.
Prefill uses one prompt, refunded on failure. Manual template selection, autosave and generation do not spend prompts.
`DRAFTING_CONFIDENCE_THRESHOLD` defaults to 0.6. AI selection is a suggestion; check every field before generating.

## Limits

This gives real model chat and original template form/preview/Word flows for testing.
Hosted Research retrieval/citation integration is implemented; independent legal accuracy and safety evaluation remain open.
The app does not yet have cross-chat memory or document-upload analysis.

## Hosted Research

Owner approved Laws.Africa Uganda Knowledge Bases on 2026-11-09, replacing local indexing/embeddings.
The latest owner instruction pauses Docker Compose/deployment; the startup commands below are reference only.
Set RETRIEVAL_PROVIDER=laws_africa and LAWS_AFRICA_API_KEY privately, then run ./scripts/dev.sh.
Research retrieves Uganda passages, generates structured segments, checks source IDs/quotations and runs
a separate support check before showing text. Source links/dates survive reload. Missing sources or
failed checks return the existing availability error and refund the prompt; no ungrounded fallback is used.
Preview coverage, independent legal accuracy, account production entitlement and dedicated safety/abstention
wording remain open. Drafting chat follow-ups now use the same hosted grounding path; template selection/rendering remain separate.

## Correct real-service startup after older sample defaults

The owner-approved templates are legitimate supplied content, not fixtures. To correct an existing
server environment that selected canned replies, run `sudo python3 scripts/configure_live.py`,
then `sudo ./scripts/dev.sh`. Missing API keys are requested privately without echoing; existing
database/storage credentials remain intact. The helper retains a configured real model or reads
the model setting from .env.example when replacing the old diagnostic model.

Normal startup does not seed sample content and fails preflight rather than serving a test model.
ENABLE_TEST_FIXTURES is false by default and required to select test providers/catalog/legal fixtures.
Automated isolated setup uses scripts/dev_env.py --test-fixtures. Diagnostic assistant records remain
stored but are excluded from normal history/model context; no user messages or documents are erased.

Current evidence and remaining acceptance are tracked in CORE_EXECUTION.md. Paid live provider tests require CIVIS_RUN_LIVE_PROVIDER_TESTS=1; ordinary checks never depend on private provider keys. Generation evaluations use independent review records and separate oracle/retrieved contexts.
