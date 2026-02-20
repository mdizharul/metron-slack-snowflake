import asyncio
import uvicorn
from fastapi import FastAPI

from app.routes.slack import router as slack_router
from app.routes.crud  import router as crud_router
from app.utils.config import PORT
from app.utils.logger import logger

app = FastAPI(
    title="Metron Security - Slack Snowflake Integration",
    description="Slack slash commands + REST API for Snowflake user operations & CRUD",
    version="2.0.0",
)

# Routes
app.include_router(slack_router)   # /slack/command  (Slack slash commands)
app.include_router(crud_router)    # /snowflake/...  (direct REST API)


@app.get("/health")
def health_check():
    return {"status": "ok"}


# Keep-alive background task — pings /health every 10 minutes
# This prevents Render free tier from sleeping during your demo
async def keep_alive():
    import httpx
    while True:
        await asyncio.sleep(600)  # every 10 minutes
        try:
            async with httpx.AsyncClient() as client:
                await client.get(
                    f"https://metron-slack-snowflake.onrender.com/health",
                    timeout=10
                )
            logger.info("Keep-alive ping sent")
        except Exception:
            pass  # silently ignore, just keep trying


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive())
    logger.info("Keep-alive task started")


# Entry point
if __name__ == "__main__":
    logger.info(f"Starting Metron Slack-Snowflake service on port {PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
