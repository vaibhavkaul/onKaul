# Hosting Architecture: ECS on EC2

**Status:** Recommended Approach
**Date:** 2026-02-13
**Owner:** Infrastructure Team

---

## Overview

Host onKaul on **AWS ECS** with hybrid approach:
- **FastAPI:** Fargate (lightweight, serverless)
- **Workers:** EC2 (heavy lifting, Docker-in-Docker)
- **All code execution stays in your VPC** (no 3rd party dependencies)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    AWS VPC (Your Cloud)                 │
│                                                         │
│  ┌────────────────┐           ┌──────────────────────┐ │
│  │  ECS Service   │           │    ECS Service       │ │
│  │   (FastAPI)    │           │    (Workers)         │ │
│  │                │           │                      │ │
│  │  • Fargate     │           │  • EC2 Launch Type   │ │
│  │  • 1-2 tasks   │           │  • 5-30 tasks        │ │
│  │  • Webhook     │           │  • Auto-scale        │ │
│  │    routing     │           │  • Docker-in-Docker  │ │
│  └───────┬────────┘           └──────────┬───────────┘ │
│          │                               │             │
│          │      ┌────────────────────┐   │             │
│          └──────►  ElastiCache Redis ◄───┘             │
│                 │  (Queue + State)   │                 │
│                 └────────────────────┘                 │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │           EC2 Auto-Scaling Group                 │  │
│  │                                                  │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ EC2 Host │  │ EC2 Host │  │ EC2 Host │      │  │
│  │  │          │  │          │  │          │      │  │
│  │  │ Worker   │  │ Worker   │  │ Worker   │      │  │
│  │  │ Tasks    │  │ Tasks    │  │ Tasks    │      │  │
│  │  │   ↓      │  │   ↓      │  │   ↓      │      │  │
│  │  │ Docker   │  │ Docker   │  │ Docker   │      │  │
│  │  │ Containers│ │ Containers│ │ Containers│     │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  │                                                  │  │
│  │  Min: 1  |  Desired: 2  |  Max: 5               │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │        AWS Secrets Manager (API Keys)            │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Components

### 1. FastAPI Service (ECS Fargate)

**Purpose:** Lightweight webhook router

**Configuration:**
- **Launch Type:** Fargate (serverless)
- **CPU:** 0.5 vCPU
- **Memory:** 1 GB
- **Task Count:** 1 (or 2 for HA)
- **Port:** 8000
- **Load Balancer:** Application Load Balancer (for Slack/Jira webhooks)

**Command:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

**What it does:**
- Receives webhooks from Slack/Jira/GitHub
- Validates signatures
- Queues jobs to Redis
- Returns 200 OK immediately (non-blocking)

**Cost:** ~$15/month

---

### 2. Worker Service (ECS on EC2)

**Purpose:** Heavy lifting - investigation and fix execution

**Configuration:**
- **Launch Type:** EC2 (not Fargate)
- **Instance Type:** c5.2xlarge (8 vCPU, 16 GB RAM)
- **Task Count:** 5-30 (auto-scales)
- **Docker Socket:** Mounted from host (`/var/run/docker.sock`)
- **Auto-Scaling:** Based on CPU and queue depth

**Command:**
```bash
python -m bee.worker
```

**What it does:**
- Pulls jobs from Redis queue
- Investigates issues (Sentry, Datadog, GitHub, etc.)
- Spawns Docker containers for fix execution
- Runs tests, creates PRs
- Posts results back to Slack/Jira

**Cost:** ~$240/month (2 instances × c5.2xlarge)

---

### 3. ElastiCache Redis

**Purpose:** Job queue + state storage

**Configuration:**
- **Instance:** cache.t3.small
- **Engine:** Redis 7.x
- **Availability:** Multi-AZ for HA

**Used for:**
- Job queue (via RQ)
- Approval flow state (fix contexts)
- TTL: 7 days for approval contexts

**Cost:** ~$25/month

---

### 4. AWS Secrets Manager

**Purpose:** Centralized secret management

**Secrets Stored:**
- `ANTHROPIC_API_KEY`
- `SLACK_BOT_TOKEN`
- `JIRA_API_TOKEN`
- `GITHUB_TOKEN`
- `SENTRY_TOKEN`
- `DATADOG_API_KEY`

**Cost:** ~$2/month

---

## Docker-in-Docker Setup

### Why Workers Need EC2 (Not Fargate)

**Challenge:** Workers need to execute code in isolated Docker containers

**Solution:** Mount Docker socket from EC2 host

### ECS Task Definition (Workers)

```json
{
  "family": "onkaul-workers",
  "networkMode": "bridge",
  "requiresCompatibilities": ["EC2"],
  "containerDefinitions": [{
    "name": "worker",
    "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/onkaul:latest",
    "command": ["python", "-m", "bee.worker"],
    "memory": 2048,
    "cpu": 1024,
    "mountPoints": [{
      "sourceVolume": "docker-socket",
      "containerPath": "/var/run/docker.sock"
    }],
    "environment": [
      {"name": "REDIS_URL", "value": "redis://redis.xxxxx.cache.amazonaws.com:6379"},
      {"name": "EXECUTOR_TYPE", "value": "docker"}
    ]
  }],
  "volumes": [{
    "name": "docker-socket",
    "host": {"sourcePath": "/var/run/docker.sock"}
  }]
}
```

**Key:** Mounting `/var/run/docker.sock` allows worker containers to spawn Docker containers on the host.

---

## EC2 Instance Configuration

### Launch Template

**AMI:** Amazon ECS-optimized Amazon Linux 2
**Instance Type:** c5.2xlarge (8 vCPU, 16 GB RAM)
**IAM Role:** ECS instance role + ECR pull permissions

**User Data:**
```bash
#!/bin/bash
echo ECS_CLUSTER=onkaul-workers >> /etc/ecs/ecs.config

# Increase Docker storage
systemctl stop docker
rm -rf /var/lib/docker
mkdir /var/lib/docker

# Start Docker
systemctl start docker
systemctl enable docker
```

### Auto-Scaling Group

**Configuration:**
- **Min:** 1 instance (always have capacity)
- **Desired:** 2 instances (baseline)
- **Max:** 5 instances (peak load)

**Scaling Policy:**
- Scale up when CPU > 70%
- Scale down when CPU < 30%
- Cooldown: 5 minutes

**Capacity:**
- Each c5.2xlarge can run ~5-8 worker tasks
- 2 instances = 10-16 concurrent fixes
- 5 instances = 25-40 concurrent fixes

---

## Deployment

### Single Docker Image for Both Services

**Dockerfile:**
```dockerfile
FROM python:3.12-slim

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install system tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install gh CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] \
    https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list && \
    apt-get update && apt-get install -y gh

# Copy application
COPY . /app
WORKDIR /app

# No CMD - specified in ECS task definition
```

**Build & Push:**
```bash
# Build image
docker build -t onkaul:latest .

# Tag for ECR
docker tag onkaul:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/onkaul:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/onkaul:latest
```

### Deploy to ECS

**Update Both Services:**
```bash
# Update FastAPI service
aws ecs update-service \
  --cluster onkaul \
  --service onkaul-api \
  --force-new-deployment

# Update worker service
aws ecs update-service \
  --cluster onkaul \
  --service onkaul-workers \
  --force-new-deployment
```

**ECS Rolling Update:**
- Pulls new image
- Starts new tasks
- Drains old tasks
- Zero downtime

---

## Scaling Strategy

### FastAPI Service
- **Static:** 1-2 tasks (doesn't need scaling)
- Handles webhook bursts via queue

### Worker Service
- **Dynamic:** Auto-scales based on load

**Metrics:**
1. **CPU Utilization** (built-in)
   - Target: 70%
   - Scale up when > 70%, down when < 30%

2. **Queue Depth** (custom CloudWatch metric)
   - Target: 2 jobs per worker
   - 10 jobs in queue → 5 workers
   - 30 jobs in queue → 15 workers

**Publishing Queue Depth:**
```python
# In bee/worker.py
import boto3

cloudwatch = boto3.client('cloudwatch')

def publish_queue_depth():
    queue = Queue(connection=redis_conn)
    depth = len(queue)

    cloudwatch.put_metric_data(
        Namespace='onKaul',
        MetricData=[{
            'MetricName': 'QueueDepth',
            'Value': depth,
            'Unit': 'Count'
        }]
    )

# Publish every minute
schedule.every(1).minutes.do(publish_queue_depth)
```

---

## Cost Breakdown

### Monthly Costs (Baseline: 2 EC2 Instances)

| Component | Configuration | Cost |
|-----------|--------------|------|
| **FastAPI Service** | Fargate: 1 task × 0.5 vCPU × 1GB | $15 |
| **Worker Instances** | 2 × c5.2xlarge (on-demand) | $240 |
| **ElastiCache Redis** | cache.t3.small | $25 |
| **Application Load Balancer** | ALB + data transfer | $20 |
| **Secrets Manager** | 5-10 secrets | $2 |
| **ECR** | Image storage | $1 |
| **CloudWatch Logs** | 10 GB/month | $5 |
| **Data Transfer** | Minimal (internal VPC) | $5 |
| **Total** | | **~$313/month** |

### Cost Optimization Options

**1. Reserved Instances (EC2):**
- 1-year: Save 30% → ~$168 (vs $240)
- 3-year: Save 50% → ~$120 (vs $240)

**2. Spot Instances (Workers):**
- Save 60-70% → ~$72-96 (vs $240)
- Risk: Can be terminated (workers handle gracefully)
- Good for: Non-urgent fixes

**3. Auto-Scaling Down at Night:**
- Scale to 1 instance during off-hours
- Save ~40% on compute

**Optimized Total:** ~$200-250/month

---

## Capacity Planning

### Per Instance Capacity
- **c5.2xlarge:** 8 vCPU, 16 GB RAM
- **Concurrent Workers:** 5-8 tasks per instance
- **Each Worker:** Runs 1 fix at a time

### Scaling Scenarios

| Scenario | Instances | Worker Tasks | Concurrent Fixes | Monthly Cost |
|----------|-----------|--------------|------------------|--------------|
| **Light** | 1 | 5 | 5 | ~$150 |
| **Baseline** | 2 | 10 | 10 | ~$280 |
| **Busy** | 3 | 15 | 15 | ~$410 |
| **Peak** | 5 | 25-30 | 25-30 | ~$670 |

### Recommended Starting Point
- **Instances:** 2 (baseline)
- **Capacity:** 10 concurrent fixes
- **Auto-scale:** Up to 5 instances during peaks

---

## Security & Networking

### VPC Configuration
- **Subnets:** Private subnets for workers, public for ALB
- **Security Groups:**
  - FastAPI: Allow 443 from ALB
  - Workers: Allow egress (GitHub, Slack, Sentry APIs)
  - Redis: Allow 6379 from FastAPI + Workers only

### IAM Roles

**ECS Task Role (FastAPI + Workers):**
- `secretsmanager:GetSecretValue` (for API keys)
- `ecr:GetAuthorizationToken`, `ecr:BatchGetImage` (for pulling images)
- `logs:CreateLogStream`, `logs:PutLogEvents` (for CloudWatch)
- `cloudwatch:PutMetricData` (for queue depth metric)

**ECS Instance Role (EC2 hosts):**
- Standard ECS instance permissions
- ECR image pull permissions

### Secrets Management
- All secrets in AWS Secrets Manager
- Injected as environment variables at runtime
- No secrets in source code or Docker images
- Automatic rotation supported

---

## Monitoring & Observability

### CloudWatch Dashboards

**API Service:**
- Request count
- Error rate (5xx)
- Latency (p50, p99)

**Worker Service:**
- CPU/Memory utilization
- Task count (running/pending)
- Queue depth
- Job success/failure rate
- Average job duration

### Alarms

**Critical:**
- API service down (0 healthy tasks)
- Worker service down (0 healthy tasks)
- Redis connection failures
- Queue depth > 50 (backlog)

**Warning:**
- CPU > 90% for 5 minutes
- Memory > 90%
- Error rate > 5%

### Logging

**Centralized Logs:**
- All services → CloudWatch Logs
- Log groups:
  - `/ecs/onkaul-api`
  - `/ecs/onkaul-workers`

**Structured Logging:**
```python
{
  "timestamp": "2026-02-13T10:30:00Z",
  "level": "INFO",
  "service": "worker",
  "job_id": "fix-abc123",
  "job_type": "execute_fix",
  "message": "Fix completed successfully",
  "pr_url": "https://github.com/..."
}
```

---

## Disaster Recovery

### Backup Strategy
- **Redis:** Snapshots every 24 hours (ElastiCache automatic)
- **Code:** GitHub repository (source of truth)
- **Docker Images:** ECR image retention (keep last 10)

### Recovery Time Objectives
- **FastAPI down:** < 5 minutes (ECS auto-restart)
- **Worker down:** < 5 minutes (ECS auto-restart)
- **Redis failure:** < 15 minutes (failover to standby)
- **Full region failure:** < 1 hour (manual failover to new region)

### Failure Scenarios

**Worker Task Crashes:**
- ECS automatically restarts task
- Job retries via RQ (3 attempts)

**EC2 Instance Failure:**
- Auto-scaling group replaces instance
- Tasks rescheduled on healthy instances

**Redis Failure:**
- ElastiCache automatic failover (Multi-AZ)
- Queue restored from snapshot

---

## Migration Path

### Phase 1: Single EC2 Instance (Prototype)
**Setup:**
- 1 EC2 instance (c5.2xlarge)
- Run FastAPI + Workers + Redis on same box (Docker Compose)

**Duration:** 1 week
**Cost:** ~$120/month
**Purpose:** Validate architecture, test Docker-in-Docker

---

### Phase 2: ECS with Fargate API + 1 EC2 Worker
**Setup:**
- Move FastAPI to Fargate
- Keep 1 EC2 instance for workers
- ElastiCache Redis

**Duration:** 1 week
**Cost:** ~$150/month
**Purpose:** Production-ready, basic scale

---

### Phase 3: Auto-Scaling Workers
**Setup:**
- Add Auto-Scaling Group (2-5 instances)
- Configure scaling policies
- CloudWatch dashboards + alarms

**Duration:** 1 week
**Cost:** ~$280/month (baseline)
**Purpose:** Handle variable load, peak capacity

---

## Conclusion

**Recommended Architecture: ECS on EC2 + Local Docker**

### Benefits
✅ **All code execution in your VPC** (no 3rd party dependencies)
✅ **Cost-effective** (~$280/month for 10 concurrent fixes)
✅ **Scalable** (5 → 30 concurrent with auto-scaling)
✅ **Managed orchestration** (ECS handles scheduling, health checks)
✅ **Security** (secrets in Secrets Manager, private VPC)
✅ **Workers justified** (do real heavy lifting with Docker-in-Docker)

### Trade-offs
⚠️ Manage EC2 instances (patching, capacity planning)
⚠️ More complex than pure Fargate
⚠️ Slower startup than cloud sandboxes (~10s vs <1s)

**Worth it for:** Full control, security, cost savings at scale

---

**Next Steps:**
1. Set up AWS infrastructure (VPC, ECR, Secrets Manager)
2. Build and push Docker image
3. Create ECS task definitions
4. Deploy Phase 1 (prototype on single EC2)
5. Validate end-to-end flow
6. Scale to Phase 3 (auto-scaling workers)

---

**Document Version:** 1.0
**Last Updated:** 2026-02-13
