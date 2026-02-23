# Deploy Webapp Mode (Docker, EC2, ECS)

This guide covers the simplest paths to run the **webapp mode** (FastAPI + worker) locally with Docker, on EC2, or on ECS. Webapp mode requires **Redis** and **two processes**:

- API service: `uvicorn main:app --host 0.0.0.0 --port 8000`
- Worker service: `python -m bee.worker`

Use `/health` for health checks and set `PUBLIC_BASE_URL` to the public URL where Slack/Jira will reach your webhooks.

## Prerequisites (all targets)

1. Create `.env` from `.env.example` and fill required values.
2. Ensure `PUBLIC_BASE_URL` is set to the externally reachable URL.
3. For Slack/Jira webhooks, confirm your webhook URLs end with `/webhook/slack` or `/webhook/jira`.
4. Ensure Redis is reachable and `REDIS_URL` is set.

See `docs/configuration.md` for environment variables.

## Local Docker (fastest)

Use the provided `docker-compose.yml` which runs Redis, the API, and the worker.

```bash
cp .env.example .env
# Edit .env with your keys

docker compose up --build
```

Health check:

```bash
curl http://localhost:8000/health
```

Webhook smoke tests:

1. For local smoke tests without real Slack/Jira signatures, set these in `.env`:

```bash
SLACK_VERIFY_SIGNATURE=false
ENABLE_JIRA_WEBHOOK_VERIFICATION=false
```

2. Restart the stack if `.env` changed:

```bash
docker compose up --build
```

3. Trigger Slack webhook endpoint:

```bash
curl -X POST http://localhost:8000/webhook/slack \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "type": "app_mention",
      "channel": "C123",
      "ts": "123.456",
      "text": "@onkaul test from local docker",
      "user": "U123"
    }
  }'
```

4. Trigger Jira webhook endpoint:

```bash
curl -X POST http://localhost:8000/webhook/jira \
  -H "Content-Type: application/json" \
  -d '{
    "issue": {"key": "TEST-123"},
    "comment": {
      "body": "@onkaul test from local docker",
      "author": {"displayName": "Local Tester"}
    }
  }'
```

5. Check logs to confirm jobs were queued:

```bash
docker compose logs api bee-worker --tail=100
```

Re-enable webhook verification before exposing services publicly.

## AWS EC2 (Docker Compose)

This is the simplest AWS path: run the same Docker Compose stack on an EC2 instance.

1. Create an EC2 instance (Ubuntu or Amazon Linux) with a security group that allows inbound HTTP/HTTPS (or port 8000 for testing).
2. Install Docker and Docker Compose.
3. Copy your repo to the instance (or build from your CI) and add your `.env`.
4. Run the stack.

```bash
docker compose up --build -d
```

5. Point `PUBLIC_BASE_URL` to your EC2 public DNS or your domain.
6. Configure Slack/Jira webhooks to point to `https://your-domain/webhook/slack` and `https://your-domain/webhook/jira`.

Notes:

- For production, put an ALB or Nginx in front and use HTTPS.
- Redis can stay in Docker for a quick start, or move to ElastiCache for durability.

## AWS ECS (Fargate)

ECS is the easiest managed option. You will run **two ECS services** (API + Worker) and use Redis (ElastiCache is recommended).

### High-level steps

1. Build and push the Docker image to ECR.
2. Create a Redis instance (ElastiCache) and note its endpoint.
3. Create an ECS task definition for the API using the command `uvicorn main:app --host 0.0.0.0 --port 8000`.
4. Create an ECS task definition for the worker using the command `python -m bee.worker`.
5. Provide environment variables via Secrets Manager or SSM Parameter Store.
6. Create an ECS service for the API behind an Application Load Balancer.
7. Create an ECS service for the worker with no load balancer.
8. Set the ALB health check path to `/health`.
9. Set `PUBLIC_BASE_URL` to the ALB DNS or your custom domain.

### Example ECS settings

- Task CPU/Memory: start with 0.5 vCPU / 1GB for API and 0.5 vCPU / 1GB for Worker.
- Desired count: 1 for API and 1 for Worker to start.
- Networking: public subnets for ALB, private subnets for tasks if you have NAT.

## Common deployment pitfalls

- **Missing worker**: Slack/Jira requests will be accepted, but no response is posted. Ensure the worker is running and connected to Redis.
- **Wrong PUBLIC_BASE_URL**: Slack/Jira webhooks must be able to reach your public URL.
- **Redis unreachable**: The API and worker must use the same Redis instance.
