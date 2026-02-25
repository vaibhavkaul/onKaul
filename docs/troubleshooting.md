# Troubleshooting

## Common Issues

- **Missing env vars**: verify `.env` values and restart the server.
- **Redis not running**: start Redis or use Docker.
- **gh not authenticated**: run `gh auth login`.
- **No Slack/Jira responses**: verify webhook secrets and posting flags.
- **OpenAI `previous_response_not_found`**:
  - Set `OPENAI_STORE=true` in `.env` (recommended default), then restart.
  - If `OPENAI_STORE=false`, onKaul uses client-side conversation state and does not use `previous_response_id`.
