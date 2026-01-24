# onKaul: Internal Developer Assistant Agent

A bot that can be tagged in Jira and Slack to investigate issues, answer code questions, and provide actionable guidance.

---

## Overview

### What This Does
- Tag `@onkaul` in Slack or Jira
- Bot investigates using Sentry, GitHub, Datadog, etc.
- Bot responds with findings and actionable next steps
- V1: Outputs "what to tell Claude Code" for fixes
- V2: Actually makes PRs via hosted sandbox agents

### Architecture (High Level)

```
Slack/Jira @mention
       │
       ▼
Webhook Handler (FastAPI)
       │
       ├──▶ Immediate response ("👀 Looking into this...")
       │
       └──▶ Background task
                 │
                 ▼
           Fetch full context (thread/ticket + comments)
                 │
                 ▼
           Agent loop (Claude + tools)
                 │
                 ▼
           Post response back to Slack/Jira
```

---

# V1 Implementation

## Development Approach

**Build order**: Core functionality first, authentication/integrations later

### Phase 1: Webhook Handlers + Request/Response Flow
1. Build FastAPI webhook endpoints for Slack and Jira
2. Accept fake webhook payloads (no auth required initially)
3. Parse payloads and extract context
4. **Log all responses** to console/file instead of posting back
5. Manual testing with curl/Postman

### Phase 2: Agent Loop + Tool System
1. Build agent core with Claude API integration
2. Implement tool schemas and handlers
3. Connect webhook handlers to agent loop
4. Test with real investigation scenarios

### Phase 3: External Integrations (Later)
1. Add real Slack/Jira authentication
2. Implement actual posting to Slack/Jira
3. Add security controls (rate limiting, allowlist)
4. Deploy to production

## Scope
- Slack and Jira webhook integration
- Read-only tools: Sentry, GitHub (search + read), Datadog
- Investigation and analysis
- Responds with findings + "Claude Code prompt" for fixes
- No PR creation, no code changes

---

## 1. Webhook Payloads (Reference)

These are the payloads we'll receive from Slack and Jira. For initial development, we'll send these manually via curl/Postman.

### Slack `app_mention` event:
```json
{
  "event": {
    "type": "app_mention",
    "channel": "C123456",
    "ts": "1234567890.123456",
    "thread_ts": "1234567890.123456",
    "text": "@onkaul how do we fix this?",
    "user": "U789"
  }
}
```

Jira webhook:
```json
{
  "issue": {"key": "B2B-456"},
  "comment": {
    "body": "@onkaul can you investigate?",
    "author": {"displayName": "Sarah"}
  }
}
```

---

## 2. Phase 1 Implementation: Webhook Handlers

**Start here**: Build the skeleton - accept webhooks, log responses, no auth, no real integrations yet.

### Project Structure

```
onKaul/
├── api/
│   ├── __init__.py
│   └── webhooks.py         # Slack/Jira webhook endpoints
├── agent/
│   ├── __init__.py
│   ├── core.py             # Agent loop (Phase 2)
│   └── prompts.py          # System prompts (Phase 2)
├── clients/
│   ├── __init__.py
│   ├── slack.py            # Slack client (Phase 3 - real posting)
│   ├── jira.py             # Jira client (Phase 3 - real posting)
│   ├── sentry.py           # Sentry API client (Phase 2)
│   ├── github.py           # GitHub API client (Phase 2)
│   └── datadog.py          # Datadog API client (Phase 2)
├── tools/
│   ├── __init__.py
│   ├── schemas.py          # Tool definitions for Claude (Phase 2)
│   └── handlers.py         # Tool execution dispatcher (Phase 2)
├── worker/
│   ├── __init__.py
│   └── tasks.py            # Background task handlers
├── utils/
│   ├── __init__.py
│   └── logger.py           # Response logger (Phase 1 - log instead of post)
├── config.py               # Environment/settings
├── main.py                 # FastAPI app entrypoint
├── requirements.txt
├── plan.md                 # This file
└── README.md
```

### Phase 1 Goals

**What we're building:**
1. FastAPI webhook endpoints at `/webhook/slack` and `/webhook/jira`
2. Payload parsing and validation
3. Background task queue (using FastAPI BackgroundTasks)
4. Response logger that writes to console and file (replaces Slack/Jira posting for now)
5. Basic error handling

**What we're NOT building yet:**
- Authentication/verification of webhook requests
- Real posting to Slack/Jira
- Agent loop (just stub responses for now)
- Tool implementations
- Security controls

### Webhook Endpoints

**Requirements:**
- Accept POST requests with JSON payloads
- Parse Slack and Jira payload formats
- Extract key information (channel/issue, user message, context)
- Queue background task for investigation
- Return immediate 200 OK response
- Log all responses instead of posting back

### Response Logger

Instead of posting to Slack/Jira, we'll log responses to:
1. **Console**: Structured output with timestamp, source (Slack/Jira), response text
2. **File**: `logs/responses.jsonl` - JSON Lines format for easy parsing

**Log Format:**
```json
{
  "timestamp": "2026-01-24T12:30:00Z",
  "source": "slack",
  "channel": "C123456",
  "thread_ts": "1234567890.123456",
  "user_message": "@onkaul investigate this error",
  "response": "Investigation results...",
  "investigation_duration_ms": 1234
}
```

---

## 3. Phase 2 Implementation: Agent Loop + Tools

### System Prompt

```
You are a senior developer assistant at TapTap Send.

## Our Repositories

- **appian-frontend**: React Native mobile app (TypeScript/TSX)
- **appian-server**: Kotlin/Spring Boot backend

## Investigation Strategy

When investigating issues:
- Frontend/UI bugs → check appian-frontend
- API errors, business logic, database → check appian-server
- Check CLAUDE.md in the devbot repo for context on both projects

## Your Capabilities
- Search and read code from our repositories
- Fetch Sentry error details and stacktraces
- Query Datadog logs and metrics
- Read Slack threads and Jira tickets for context
- Use acli to query Jira issues

## Response Format

Your responses should include:

### Investigation Breadcrumbs
Show your investigation path:
🔍 Investigation path:
1. Fetched Sentry issue #12345
2. Searched for error message in appian-server
3. Found in src/api/handlers.py:142
4. Checked recent PRs touching this file

### Confidence Score
**Confidence**: 🟢 High (found exact error + fix)
**Confidence**: 🟡 Medium (found related code, need more info)
**Confidence**: 🔴 Low (couldn't locate issue)

### Impact Assessment
- **Severity**: Critical/High/Medium/Low
- **Users Affected**: Estimate or specific count from Sentry
- **Related Issues**: Link to similar Sentry issues or Jira tickets

### Findings
Clear explanation of root cause with file references (file:line)

### Claude Code Prompt
When you've identified a fix, provide:

**To fix with Claude Code:**
\```
[Clear, specific instructions including:
- Which repo and file(s) to modify
- What the problem is
- What the fix should do
- Any tests to run after]
\```
```

### Tool Schemas

**Available Tools:**

1. **get_sentry_issue**: Fetch Sentry error details, stacktraces, frequency, affected users
2. **search_code**: Search code in appian-frontend or appian-server
3. **read_file**: Read specific file contents from a repo
4. **list_directory**: List files/folders in a directory
5. **query_datadog_logs**: Search Datadog logs for runtime issues
6. **query_jira**: Use acli to search Jira issues
7. **get_jira_issue**: Fetch detailed Jira issue information
8. **web_search**: Search web for documentation, Stack Overflow, library info

---

## 4. Phase 3 Implementation: External Integrations

### Authentication & Real Posting

Once Phase 1 and 2 are working with logged responses, we'll add:

1. **Slack Integration**
   - Verify webhook signatures using SLACK_SIGNING_SECRET
   - Post responses back to Slack using Web API
   - Handle threading properly (reply in thread)

2. **Jira Integration**
   - Use `acli` for posting comments back to Jira issues
   - Format responses in Atlassian Document Format

3. **Security Controls**
   - Rate limiting per user/channel
   - Allowlist for Slack channels and Jira projects
   - Audit logging to database

### Client Implementation Strategy
- **Slack**: Use Slack Web API (REST)
- **Jira**: Use `acli` CLI under the hood (already configured)
- **Sentry**: Use Sentry REST API
- **GitHub**: Use GitHub REST API
- **Datadog**: Use Datadog API client library
- **Confluence**: Use REST API (credentials in ~/.zshrc)

All clients abstracted behind consistent Python interfaces. Implementation details (CLI vs REST) are hidden from the agent.

## Testing Approach

### Phase 1 Testing
- **Manual testing**: Use curl/Postman to send webhook payloads
- **Validation**: Check logs/responses.jsonl for correct output
- **Test cases**:
  - Slack mention with simple question
  - Jira comment with investigation request
  - Malformed payloads (error handling)

### Phase 2 Testing
- **Mock tool responses**: Test agent loop without real API calls
- **Real API testing**: Test individual tools with actual Sentry/GitHub/Datadog
- **Investigation scenarios**:
  - Find Sentry error and suggest fix
  - Search code for specific function
  - Query Datadog logs for errors

### Phase 3 Testing
- **Slack workspace**: Test in dedicated test channel
- **Jira project**: Test with sample test tickets
- **End-to-end**: Full flow from @mention to posted response
- **Load testing**: Concurrent requests, rate limiting

---

# V2 Implementation (Future)

## Scope
- Hosted sandbox agents that can make code changes
- Full PR creation workflow
- Run tests, type checking, linting before submitting
- Reads CLAUDE.md context from devbot repo

## V2 Considerations (from review)

**Concerns:**
- **Cost**: Running warm sandboxes is expensive
- **Security**: Untrusted code execution risk
- **Complexity**: Much harder than V1

**Alternative Approaches:**
1. Generate Git patches/diffs, let developers apply them
2. Use GitHub Codespaces API on-demand (no warm pool needed)
3. Start with simpler actions first:
   - Create Jira tickets for bugs found during investigation
   - Comment on existing PRs when mentioned
   - Review code and spot issues
   - Link PRs to Jira tickets automatically

**Recommendation**: Prove value with V1 first, then evaluate if V2 is needed. Developers may prefer receiving clear instructions over automated PRs.

---

# Implementation Checklist

## Phase 1: Webhook Handlers
- [ ] FastAPI project setup with requirements.txt
- [ ] `/webhook/slack` endpoint created
- [ ] `/webhook/jira` endpoint created
- [ ] Payload parsing for Slack app_mention events
- [ ] Payload parsing for Jira comment webhooks
- [ ] Background task queue setup (FastAPI BackgroundTasks)
- [ ] Response logger implementation (console + file)
- [ ] Basic error handling
- [ ] Manual testing with curl/Postman
- [ ] Sample webhook payloads documented

## Phase 2: Agent Loop + Tools
- [ ] Anthropic API client setup
- [ ] Agent loop implementation with tool use
- [ ] System prompt created with TapTap Send context
- [ ] Tool schemas defined (Sentry, GitHub, Datadog, Jira)
- [ ] Tool handlers implemented
- [ ] Sentry client (API)
- [ ] GitHub client (API)
- [ ] Datadog client (API)
- [ ] Jira client (acli)
- [ ] Connect agent to webhook handlers
- [ ] Test end-to-end with real investigation scenarios
- [ ] Response formatting (breadcrumbs, confidence, impact, Claude Code prompt)

## Phase 3: External Integrations
- [ ] Slack app created and configured
- [ ] Slack webhook signature verification
- [ ] Slack posting implementation (replace logger)
- [ ] Jira automation rule set up
- [ ] Jira posting implementation via acli (replace logger)
- [ ] Security controls (rate limiting, allowlist, audit logging)
- [ ] Error redaction (sensitive data)
- [ ] Caching layer
- [ ] Unit tests
- [ ] Integration tests
- [ ] End-to-end test in test Slack workspace
- [ ] Load testing
- [ ] Deploy to production
- [ ] Monitoring/alerting

## V2 Planning Checklist (Future)
- [ ] Decide on sandbox provider (E2B, Codespaces, etc.)
- [ ] Define which repos allow PR creation
- [ ] Ensure CLAUDE.md exists in devbot repo with latest context
- [ ] Define validation requirements per repo (tests, linting, type checking)
- [ ] Plan rollback/cleanup for failed PRs
- [ ] Design approval workflow (auto-merge vs. human review)
