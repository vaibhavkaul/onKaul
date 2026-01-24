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

## Scope
- Slack and Jira webhook integration
- Read-only tools: Sentry, GitHub (search + read), Datadog
- Investigation and analysis
- Responds with findings + "Claude Code prompt" for fixes
- No PR creation, no code changes

---

## 1. Trigger Layer

### Slack Setup
- Create Slack App with bot user at api.slack.com/apps
- Bot token scopes needed:
  - `app_mentions:read` (receive @mentions)
  - `channels:history` (read public channel messages)
  - `groups:history` (read private channel messages)
  - `chat:write` (post responses)
- Enable Event Subscriptions, subscribe to `app_mention` event
- Set Request URL to your webhook endpoint

### Jira Setup
- Use existing `acli` (Atlassian CLI) integration
- Jira Automation:
  - Trigger: "When a comment is added"
  - Condition: Comment contains `@onkaul`
  - Action: Send webhook to your endpoint
  - Payload should include: `{{issue.key}}`, `{{comment.body}}`, `{{comment.author}}`

### Webhook Payloads

Slack `app_mention` event:
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

## 2. Webhook Handlers

### Project Structure

```
onKaul/
├── api/
│   ├── __init__.py
│   └── webhooks.py         # Slack/Jira webhook endpoints
├── agent/
│   ├── __init__.py
│   ├── core.py             # Agent loop
│   └── prompts.py          # System prompts
├── clients/
│   ├── __init__.py
│   ├── slack.py            # Slack API client
│   ├── jira.py             # Jira client (uses acli)
│   ├── sentry.py           # Sentry API client
│   ├── github.py           # GitHub API client
│   └── datadog.py          # Datadog API client
├── tools/
│   ├── __init__.py
│   ├── schemas.py          # Tool definitions for Claude
│   └── handlers.py         # Tool execution dispatcher
├── worker/
│   ├── __init__.py
│   └── tasks.py            # Background task handlers
├── config.py               # Environment/settings
├── main.py                 # FastAPI app entrypoint
├── requirements.txt
├── plan.md                 # This file
└── README.md
```

---

## 3. Tool Definitions

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

## 4. Client Implementations

### Strategy
- **Slack**: Use Slack Web API (REST)
- **Jira**: Use `acli` CLI under the hood (already configured)
- **Sentry**: Use Sentry REST API
- **GitHub**: Use GitHub REST API
- **Datadog**: Use Datadog API client library
- **Confluence**: Use REST API (credentials in ~/.zshrc)

All clients abstracted behind consistent Python interfaces. Implementation details (CLI vs REST) are hidden from the agent.

---

## 5. Security & Operations

### Security Controls
- **Rate limiting**: Prevent abuse and runaway costs
- **Allowlist**: Specific Slack channels/Jira projects can use the bot
- **Audit logging**: Track all investigations (timestamp, user, query, response)
- **Secrets handling**: Never expose API keys, tokens, database credentials in responses
- **Error redaction**: Strip sensitive data from stacktraces before showing

### Error Handling Patterns
- **Slack thread too long**: Summarize or ask user to provide specific context
- **Sentry issue not found**: Return graceful error message
- **GitHub rate limits**: Implement exponential backoff and retry
- **Agent timeout**: Maximum 60 seconds, return "still investigating" message
- **Tool failures**: Continue with partial results, note what failed

### Caching Strategy
- Cache Sentry issues for 15 minutes (reduce API calls for repeated questions)
- Cache GitHub file reads for 5 minutes
- Cache Jira issue details for 10 minutes
- No caching for Datadog logs (always fresh)

---

## 6. Testing Strategy

### Unit Tests
- Test each client independently with mocked APIs
- Test tool handlers with fixture data
- Test webhook payload parsing

### Integration Tests
- Mock external APIs (Slack, Jira, Sentry, GitHub, Datadog)
- Test agent loop with predefined tool sequences
- Test error handling paths

### End-to-End Tests
- Use test Slack workspace with dedicated test channel
- Use test Jira project with sample tickets
- Test full investigation flow from @mention to response

### Load Testing
- Test concurrent @mentions (10+ simultaneous)
- Test long-running investigations (near timeout)
- Test rate limiting behavior

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

## V1 Launch Checklist
- [ ] Slack app created and configured
- [ ] Jira automation rule set up
- [ ] All API tokens provisioned (Slack, Jira, GitHub, Sentry, Anthropic)
- [ ] Webhook endpoints deployed and accessible
- [ ] Tool schemas populated with actual repo names
- [ ] System prompt customized with TapTap Send context
- [ ] Security controls implemented (rate limiting, allowlist, audit logging)
- [ ] Error handling and redaction in place
- [ ] Caching layer implemented
- [ ] Unit tests written
- [ ] Integration tests written
- [ ] End-to-end test completed in test Slack workspace
- [ ] Load testing completed
- [ ] Deployed to production environment
- [ ] Monitoring/alerting configured

## V2 Planning Checklist (Future)
- [ ] Decide on sandbox provider (E2B, Codespaces, etc.)
- [ ] Define which repos allow PR creation
- [ ] Ensure CLAUDE.md exists in devbot repo with latest context
- [ ] Define validation requirements per repo (tests, linting, type checking)
- [ ] Plan rollback/cleanup for failed PRs
- [ ] Design approval workflow (auto-merge vs. human review)
