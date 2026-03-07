# Repository Config

The repository config tells onKaul what repos you have, what they do, and how to route investigations.

## Why This Matters

- Helps the agent pick the right codebase
- Adds domain context (tech stack + key systems)
- Improves investigation accuracy and speed

## How to Use Each Section

- `repositories`: your repo catalog. Use `tech_stack`, `key_systems`, and `handles` to help the agent choose the right repo.
- `investigation_strategy`: map common issue categories to a default repo.
- `additional_context`: pointers to internal docs (playbooks, runbooks, commands).

## Sandbox (Live Preview)

Add `hotReloadSupport` and a `sandbox` block to any repo to enable the live preview + Claude Code terminal in the web UI. See [docs/sandbox.md](./sandbox.md) for full details.

```json
"my-site": {
  "name": "my-site",
  "org": "acme",
  "hotReloadSupport": true,
  "sandbox": {
    "appType": "static",
    "previewPort": 8080,
    "startCommand": ""
  }
}
```

## Example

```json
{
  "repositories": {
    "merchant-console": {
      "name": "merchant-console",
      "org": "acme",
      "description": "Merchant operations web console",
      "tech_stack": [
        "React 19 + TypeScript",
        "Vite",
        "React Router",
        "Material-UI + TailwindCSS"
      ],
      "key_systems": ["Auth", "Payouts", "Disputes"],
      "handles": ["UI bugs", "Console crashes", "Performance regressions"],
      "context_files": []
    },
    "core-api": {
      "name": "core-api",
      "org": "acme",
      "description": "Core backend API service",
      "tech_stack": [
        "Python/FastAPI",
        "PostgreSQL + SQLModel",
        "Alembic (migrations)"
      ],
      "key_systems": ["API", "Billing", "Webhooks"],
      "handles": ["API errors", "DB issues", "Latency spikes"],
      "context_files": []
    },
    "mobile-app": {
      "name": "mobile-app",
      "org": "acme",
      "description": "React Native mobile application",
      "tech_stack": [
        "React Native",
        "TypeScript/TSX",
        "Redux (state management)",
        "GraphQL (with code generation)",
        "XState (state machines)",
        "Jest (unit tests)",
        "Detox (E2E tests)"
      ],
      "key_systems": ["Wallet", "Onboarding", "Transfers"],
      "handles": ["App crashes", "Mobile UI bugs", "Sync issues"],
      "context_files": []
    }
  },
  "investigation_strategy": {
    "Frontend/UI bugs": "merchant-console",
    "API errors": "core-api",
    "Database issues": "core-api",
    "Mobile crashes": "mobile-app"
  },
  "additional_context": {
    "Sentry Integration": "/path/to/sentry-integration.md",
    "Jira Workflows": "/path/to/jira-commands.md",
    "Confluence Wiki": "/path/to/confluence-wiki.md"
  }
}
```
