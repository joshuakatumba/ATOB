> Current owner scope (2026-11-07): integrate the supplied React 18/plain JSX/Vite UI with existing FastAPI/SuperTokens services. Preserve markup, copy and CSS. The earlier Next.js rebuild and milestone ordering below are historical; current scope and evidence are tracked in STATUS.md.

# M2 chat and web workspace

Adds owned conversation CRUD, feedback, streamed model responses, quota refunds before the
first token, persisted incomplete replies, two-stream leases and hourly limits. Real Anthropic
streaming is behind an environment-configured provider; local development uses labelled FAKE data.
Adds the Next.js workspace, browser auth screens, modes, stop, theme, settings, legal-content
mechanism and PWA shell. Legal text remains owner-provided; FAKE legal records contain labels only.

Backend ownership, schema/quota, failure/refund and nginx heartbeat/disconnect tests pass.
The full backend run had 28 passes, one optional smoke skip and one random password-policy
fixture error; strengthening generated passwords made that targeted rerun pass. Typecheck, lint
and the frontend production build pass. Public/mobile/PWA browser checks pass. Browser signup
and reset flows still fail after one local fix cycle and are recorded in KNOWN_ISSUES.md.
M2 is not complete until final CI and the browser acceptance pass.

Account deletion/export jobs remain M5 work; uploads remain disabled. Real retrieval, approved
content and production deployment are later gated milestones.

## Dependency justification

| Package | Pin | One-line justification |
|---|---|---|
| next / eslint-config-next | 16.4.5 | Required App Router application and framework lint rules. |
| react / react-dom | 19.3.1 | Interactive workspace and auth screens. |
| supertokens-web-js | 0.15.0 | Provider-owned browser sessions and all five auth flows. |
| typescript | 5.9.3 | Strict frontend typechecking. |
| tailwindcss / @tailwindcss/postcss | 4.3.5 | Required styling stack and its build integration. |
| postcss | 8.5.32 | CSS processing; updated to remove the detected high advisory. |
| eslint | 9.39.1 | Frontend lint runner, compatible with pinned Next configuration. |
| @types/node | 22.15.30 | Build/test Node types. |
| @types/react / @types/react-dom | 19.2.2 | Strict React/DOM types. |
| @playwright/test | 1.65.0 | Real browser integration tests. |
| langfuse | 3.1.0 | LLM traces containing technical metadata and usage only. |
| anyio | 4.16.0 (existing lock) | Shield persistence/refunds during client disconnect cleanup. |

Official API references consulted: pinned Next 16.4.5 server/client guide, React 19.3 hooks,
TypeScript 5.9 release notes, Tailwind 4.3 Next guide, installed SuperTokens 0.15 declarations,
Playwright 1.65 vendor types, AnyIO 4.16 cancellation/shielding docs, Anthropic streaming API,
and Langfuse 3.1.0 client source/signatures. npm transitive versions are frozen in package-lock.json.

- https://raw.githubusercontent.com/vercel/next.js/v16.4.5/docs/01-app/01-getting-started/05-server-and-client-components.mdx
- https://react.dev/reference/react/useState
- https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-9.html
- https://tailwindcss.com/docs/installation/framework-guides/nextjs
- https://anyio.readthedocs.io/en/stable/cancellation.html
- https://platform.claude.com/docs/en/build-with-claude/streaming
- https://raw.githubusercontent.com/langfuse/langfuse-python/v3.1.0/langfuse/_client/client.py

Eight moderate npm advisories remain for M6 audit; the detected high PostCSS advisory was fixed.
