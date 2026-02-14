# Worker Bee Architecture: Scalable Task Execution for onKaul

**Status:** Proposed
**Date:** 2026-02-13
**Author:** Architecture Discussion

---

## Executive Summary

Transform onKaul from a blocking, single-threaded investigation bot into a scalable, distributed system capable of handling 25-30+ concurrent tasks by introducing **Worker Bees** - isolated execution environments that handle both investigation and fix implementation.

**Key Changes:**
- FastAPI becomes thin webhook router (non-blocking)
- Worker bees handle all investigation + execution
- Redis-based approval flow for human-in-the-loop fixes
- Isolated workspaces (Docker or E2B) for safe code execution
- Horizontal scaling: 1 → 30 workers with simple config change

---

## Current Architecture (Problem)

```
Slack/Jira Webhook
       ↓
 onKaul FastAPI
       ↓
 Inline Investigation (blocks webhook handler)
       ↓
 Posts Result to Slack/Jira
```

**Issues:**
- ❌ Blocking: Each webhook handler waits for investigation (5-10 min)
- ❌ No concurrency: Can't handle multiple requests simultaneously
- ❌ No isolation: Can't safely execute code/run tests
- ❌ No fix implementation: Only investigates, doesn't fix

---

## New Architecture (Solution)

```
Slack/Jira/GitHub Webhooks
         ↓
    onKaul FastAPI (thin, instant response)
         ↓
    Redis Queue (RQ)
         ↓
    Worker Bee Pool (5-30 workers)
         ↓
    Execution Environment (Docker or E2B sandboxes)
         ↓
    Posts Results → Slack/Jira/GitHub
```

**Benefits:**
- ✅ Non-blocking: FastAPI returns instantly
- ✅ Concurrent: 30 bees = 30 parallel tasks
- ✅ Isolated: Each task in separate workspace
- ✅ Safe execution: Run tests, linters, create PRs
- ✅ Scalable: Add workers = add capacity

---

## Core Components

### 1. Thin FastAPI (Webhook Router)

**Responsibility:** Validate webhooks, queue jobs, nothing else

**Endpoints:**
- `POST /webhook/slack` - Queue investigation or execution job
- `POST /webhook/jira` - Queue investigation job
- `POST /webhook/github` - Queue PR review job

**What it does:**
```
1. Receive webhook
2. Validate signature (optional)
3. Determine job type (investigate / execute_fix / review_pr)
4. Queue job with minimal payload
5. Return 200 OK (instant)
```

**What it DOESN'T do:**
- No investigation logic
- No API calls to Sentry/Datadog/etc.
- No posting to Slack/Jira (bees do this)

---

### 2. Worker Bees (Fat Workers)

**Responsibility:** Do ALL the work

**Shared Configuration:**
- Same `.env` as FastAPI
- Same tools: Sentry, Datadog, GitHub, Jira, Slack clients
- Same agent logic: `agent/core.py`, `tools/`, `clients/`

**Job Types:**

#### Job Type 1: Investigation
```python
{
    "type": "investigate",
    "source": "slack",  # or "jira"
    "event": {
        # Raw webhook event (channel, thread_ts, text, user, etc.)
    }
}
```

**What bee does:**
1. Picks up job from queue
2. Extracts user message + context
3. Runs investigation using Claude + tools (Sentry, Datadog, GitHub, etc.)
4. Posts findings to Slack/Jira
5. If fix proposed: stores context in Redis, asks for approval
6. Exits

**Duration:** 5-10 minutes

#### Job Type 2: Fix Execution
```python
{
    "type": "execute_fix",
    "redis_key": "fix:abc123"  # Points to full context
}
```

**What bee does:**
1. Picks up job from queue
2. Fetches fix context from Redis using key
3. Spins up isolated workspace (Docker/E2B)
4. Clones repo, creates branch
5. Uses Claude to implement fix (edit files, run commands)
6. Runs tests + linters
7. Creates PR
8. Posts PR link to original Slack/Jira thread
9. Deletes Redis key (cleanup)
10. Exits

**Duration:** 10-30 minutes

---

### 3. Redis (Queue + State)

**Two Roles:**

**Role 1: Job Queue (via RQ)**
- Stores pending jobs
- Workers pull jobs (FIFO)
- Handles retries, failures

**Role 2: State Storage**
- Stores fix contexts between investigation and execution
- Stores approval pointers

**Storage Pattern:**
```
fix:{id} → {repo, branch, approach, investigation, destination, ...}
approval:{channel}:{message_ts} → {fix_key: "fix:{id}"}
```

**Lifecycle:**
1. Bee-1 stores fix context + approval pointer
2. User approves
3. FastAPI reads approval pointer, gets fix key
4. FastAPI queues execution job with just the key
5. Bee-2 fetches full context using key
6. Bee-2 deletes key after execution

**TTL:** 7 days (auto-cleanup of stale approvals)

**Size Handling:** Redis directly (supports up to 512MB per value, typical plan is 100-500KB)

---

## Approval Flow (Human-in-the-Loop)

### Phase 1: Investigation

```
1. User: "@onkaul fix payment timeout"
   ↓
2. Slack → onKaul FastAPI
   ↓
3. FastAPI queues: {type: "investigate", event: {...}}
   ↓
4. Bee-1 picks up job
   ↓
5. Bee-1 investigates (Sentry, GitHub, Datadog, etc.)
   ↓
6. Bee-1 posts to Slack:
   "🔍 Found issue: PaymentProcessor.process() null pointer
    📋 Proposed Fix: Add null check at line 145
    React ✅ to approve"
   ↓
7. Bee-1 stores in Redis:
   - fix:abc123 → {repo, approach, investigation, destination}
   - approval:C123:1707849456 → {fix_key: "fix:abc123"}
   ↓
8. Bee-1 EXITS (job done)
```

### Phase 2: User Approval

```
9. User reacts with ✅ to Slack message
   ↓
10. Slack sends reaction_added webhook to FastAPI
   ↓
11. FastAPI receives: {channel, message_ts, reaction: "✅"}
```

### Phase 3: Execution Dispatch

```
12. FastAPI checks Redis: GET approval:C123:1707849456
    ↓
13. Gets back: {fix_key: "fix:abc123"}
    ↓
14. FastAPI queues: {type: "execute_fix", redis_key: "fix:abc123"}
    ↓
15. FastAPI deletes: approval:C123:1707849456
```

### Phase 4: Fix Implementation

```
16. Bee-2 picks up execute_fix job
    ↓
17. Bee-2 fetches: GET fix:abc123 → {full context}
    ↓
18. Bee-2 posts: "🐝 Starting implementation..."
    ↓
19. Bee-2 spins up isolated workspace (Docker/E2B)
    ↓
20. Bee-2 clones repo, creates branch
    ↓
21. Bee-2 uses Claude to implement fix:
    - Edit files
    - Run commands
    - Check work
    ↓
22. Bee-2 runs: pytest, ruff, etc.
    ↓
23. Bee-2 creates PR via gh CLI
    ↓
24. Bee-2 posts to Slack: "✅ PR created: github.com/..."
    ↓
25. Bee-2 deletes: fix:abc123
    ↓
26. Bee-2 EXITS
```

**Key Insight:** Bee-1 and Bee-2 are likely different worker processes. Redis bridges them.

---

## Execution Environment Options

### Option A: Docker Containers (Recommended Start)

**How it works:**
- Build Docker image with all dev tools (git, gh, Python, Node, pytest, ruff, etc.)
- Each fix execution spins up fresh container
- Bee runs commands inside container via Docker SDK
- Container destroyed after job

**Pros:**
- ✅ Simple setup (just Docker)
- ✅ True isolation per task
- ✅ Local - no external dependencies
- ✅ Full control over environment

**Cons:**
- ❌ Container startup overhead (~5-10s)
- ❌ Resource intensive (each container needs RAM/CPU)
- ❌ Limited concurrency on single machine (~5-10)

**Scale:** Good for 5-10 concurrent tasks on decent hardware

**Cost:** Infrastructure only (~$100-200/mo for worker machine)

---

### Option B: E2B Code Sandboxes (Recommended Scale)

**How it works:**
- Use [E2B](https://e2b.dev) - cloud sandboxes
- API call creates fresh sandbox (<1s startup)
- Bee executes commands via E2B SDK
- Sandbox destroyed after job

**Pros:**
- ✅ Near-instant startup (<1s)
- ✅ Scales to 30+ concurrent easily
- ✅ VM-level isolation
- ✅ No infrastructure to manage
- ✅ Built-in filesystem, process management

**Cons:**
- ❌ External dependency
- ❌ Cost per execution (~$0.10-0.30 per task)
- ❌ Network latency

**Scale:** Excellent for 25-30+ concurrent tasks

**Cost:** ~$0.10-0.30 per fix (pay per use)

---

### Abstraction Layer

**Design for swappable executors:**

```python
class WorkspaceExecutor(ABC):
    def clone_repo(repo: str)
    def run_command(cmd: str) → Result
    def read_file(path: str) → str
    def write_file(path: str, content: str)
    def create_pr() → str

class DockerExecutor(WorkspaceExecutor):
    # Docker implementation

class E2BExecutor(WorkspaceExecutor):
    # E2B implementation

# In config
EXECUTOR_TYPE = os.getenv("EXECUTOR_TYPE", "docker")  # or "e2b"
```

**Start with Docker, migrate to E2B when scaling.**

---

## Shared Configuration

**Both FastAPI and all bees use same `.env`:**

```bash
# Agent
ANTHROPIC_API_KEY=sk-ant-...

# Posting responses
SLACK_BOT_TOKEN=xoxb-...
JIRA_API_TOKEN=ATATT3xFfGF0...
JIRA_BASE_URL=https://taptapsend.atlassian.net
JIRA_EMAIL=bot@taptapsend.com

# Creating PRs
GITHUB_TOKEN=ghp_...
GITHUB_ORG=taptapsend

# Investigation tools
SENTRY_TOKEN=sntrys_...
SENTRY_ORG=taptapsend
DATADOG_API_KEY=...
DATADOG_APP_KEY=...

# Queue + state
REDIS_URL=redis://localhost:6379

# Execution
EXECUTOR_TYPE=docker  # or "e2b"
E2B_API_KEY=...  # if using E2B
```

**Security Model:** Shared credentials acceptable for internal tool. All workers trust same config.

---

## File Structure Changes

### Keep (Reuse Existing)
```
agent/
  core.py              # Investigation logic (reused by bees)
  prompts.py           # System prompts
clients/
  sentry.py            # Sentry API client
  github.py            # GitHub CLI wrapper
  datadog.py           # Datadog API
  slack.py             # Slack API
  jira.py              # Jira CLI wrapper
tools/
  schemas.py           # Tool definitions for Claude
  handlers.py          # Tool execution
config.py              # Environment config (shared)
```

### New
```
bee/
  __init__.py
  tasks.py             # Job handlers (investigate, execute_fix)
  worker.py            # RQ worker process entrypoint
  executors/
    __init__.py
    base.py            # WorkspaceExecutor ABC
    docker.py          # Docker implementation
    e2b.py             # E2B implementation
  storage.py           # PayloadStorage (Redis wrapper)
plan/
  worker-bee-architecture.md  # This document
```

### Modify
```
api/
  webhooks.py          # Refactor to thin router (queue jobs)
main.py                # Simpler, just webhook routing
```

---

## Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Thin webhook receiver (1 instance)
  onkaul-api:
    build: .
    env_file: .env
    ports:
      - "8000:8000"
    command: uvicorn main:app --host 0.0.0.0 --port 8000
    depends_on:
      - redis

  # Worker bees (scale these!)
  bee-worker:
    build: .
    env_file: .env
    command: python -m bee.worker
    depends_on:
      - redis
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # For Docker executor
```

### Scaling

**Start with 1 worker:**
```bash
docker-compose up
```

**Scale to 10 workers:**
```bash
docker-compose up --scale bee-worker=10
```

**Scale to 30 workers (if using E2B):**
```bash
docker-compose up --scale bee-worker=30
```

---

## Migration Path

### Phase 1: Add Queue Infrastructure (Non-Breaking)
**Goal:** Set up Redis + basic worker without changing current behavior

**Tasks:**
- Add Redis to docker-compose
- Add RQ dependency
- Create `bee/worker.py` skeleton
- Create `bee/tasks.py` with single `investigate()` function
- Keep current FastAPI investigation logic (don't break anything)
- Test: Queue a dummy job, verify worker picks it up

**Validation:** Worker can process jobs, FastAPI still works as before

---

### Phase 2: Move Investigation to Bees
**Goal:** Make FastAPI thin, move investigation to workers

**Tasks:**
- Refactor `api/webhooks.py` to queue jobs instead of investigating inline
- Move investigation logic from webhooks to `bee/tasks.investigate()`
- Reuse existing `agent/core.py`, `clients/`, `tools/`
- Test: @onkaul in Slack → queues job → bee investigates → posts result

**Validation:** Investigation works same as before, but asynchronously

---

### Phase 3: Add Approval Flow
**Goal:** Enable human-in-the-loop approval before fixes

**Tasks:**
- Create `bee/storage.py` (Redis wrapper)
- When investigation proposes fix: store context, ask for approval
- Handle Slack reactions in FastAPI
- Test: Investigate → approve with ✅ → verify state flow

**Validation:** Approval request posted, context stored/retrieved correctly

---

### Phase 4: Add Fix Execution
**Goal:** Implement the actual fix after approval

**Tasks:**
- Create `bee/executors/docker.py` (Docker workspace)
- Create `bee/tasks.execute_fix()` function
- Implement: clone repo, edit files, run tests, create PR
- Give Claude tools to edit files + run commands
- Test: Full flow (investigate → approve → fix → PR)

**Validation:** End-to-end fix creation with PR

---

### Phase 5: Scale & Optimize
**Goal:** Handle 25-30 concurrent tasks

**Tasks:**
- Scale workers: `docker-compose up --scale bee-worker=10`
- Load test with multiple simultaneous requests
- Monitor Redis memory usage
- Optionally: Implement `bee/executors/e2b.py` for better scale
- Add monitoring/alerting

**Validation:** Can handle 25-30 concurrent investigations/fixes

---

## Success Metrics

**Performance:**
- FastAPI response time: <100ms (instant webhook response)
- Investigation time: 5-10 minutes (unchanged)
- Fix execution time: 10-30 minutes
- Concurrent capacity: 25-30 tasks

**Reliability:**
- Worker crash → job retries automatically (RQ built-in)
- Redis down → graceful degradation (queue later)
- Isolated failures (one bee failure doesn't affect others)

**Scalability:**
- Horizontal: Add workers = add capacity (linear scaling)
- Cost: ~$0.10-0.30 per fix with E2B, or infrastructure cost with Docker

---

## Security Considerations

**Shared Credentials:**
- All workers use same tokens (SLACK_BOT_TOKEN, GITHUB_TOKEN, etc.)
- Acceptable for internal tool in trusted environment
- Future: Could use secret rotation, least privilege per worker

**Code Execution:**
- Fixes run in isolated sandboxes (Docker containers or E2B VMs)
- No access to host system
- Timeouts prevent runaway processes

**Redis Security:**
- Use Redis AUTH if exposed
- TTL on all keys (7 days) prevents unbounded growth
- No sensitive data in keys (only IDs)

---

## Future Enhancements

**V2 Features (Post-MVP):**
- Temporal workflow engine (better than Redis for long-running approvals)
- Kubernetes deployment (production-grade orchestration)
- Multi-region workers (reduce latency)
- Priority queues (urgent fixes jump the line)
- Approval via Slack interactive buttons (not just reactions)
- Fix preview (show diff before approval)
- Rollback capability (revert bad fixes)
- Analytics dashboard (track fix success rate, time to resolution)

---

## Open Questions

1. **Approval timeout:** What if user never approves? (Current: 7 day TTL, then auto-expire)
2. **Failed fixes:** Should bee retry? Post error? (Current: Post error to thread)
3. **Long-running fixes:** What if fix takes >30 min? (Current: Job timeout, need to adjust)
4. **Multiple approvers:** Should we require N approvals? (Current: Single ✅)
5. **Fix conflicts:** What if fix branch conflicts with main? (Current: PR shows conflict, manual resolution)

---

## Conclusion

This architecture transforms onKaul from a simple investigation bot into a **scalable, autonomous fix implementation system**. By introducing worker bees, isolated execution environments, and a Redis-based approval flow, we enable:

- **30x scale:** From 1 concurrent task to 30
- **Safe execution:** Isolated workspaces for testing and PRs
- **Human oversight:** Approval flow before making changes
- **Flexible deployment:** Start with Docker, scale to E2B

**Next Steps:**
1. Review and approve this plan
2. Begin Phase 1 (add queue infrastructure)
3. Iterate through migration phases
4. Scale to production capacity

---

**Document Version:** 1.0
**Last Updated:** 2026-02-13
