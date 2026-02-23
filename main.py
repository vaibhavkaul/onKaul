"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from api.webhooks import router as webhook_router
from config import config

# Create FastAPI app
app = FastAPI(
    title=config.APP_NAME,
    description="Open-source developer assistant agent",
    version="0.1.0",
    debug=config.DEBUG,
)

# Include routers
app.include_router(webhook_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "app": config.APP_NAME,
        "status": "running",
        "phase": "1 - Webhook Handlers",
        "public_base_url": config.PUBLIC_BASE_URL,
        "endpoints": {
            "slack": "/webhook/slack",
            "jira": "/webhook/jira",
        },
    }


@app.get("/health")
async def health():
    """Health check for monitoring."""
    return JSONResponse(content={"status": "healthy"}, status_code=200)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower(),
    )
