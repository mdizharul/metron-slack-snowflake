import uvicorn
from fastapi import FastAPI

from app.routes.slack import router as slack_router
from app.utils.config import PORT
from app.utils.logger import logger

app = FastAPI(
    title="Metron Security – Slack Snowflake Integration",
    description="Slack slash commands for Snowflake user operations",
    version="1.0.0",
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(slack_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"Starting Metron Slack-Snowflake service on port {PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
