import httpx
from app.utils.logger import logger


async def send_delayed_response(response_url: str, text: str, in_channel: bool = False) -> None:
    """
    Posts a delayed response back to Slack via response_url.

    Why delayed?
    Slack requires an HTTP 200 within 3 seconds of receiving the slash command.
    Because Snowflake operations can take longer, the route immediately returns
    a 200 ACK, then calls this function (in a background task) to deliver the
    real result.

    response_type:
        ephemeral  — only visible to the user who ran the command (default)
        in_channel — visible to everyone in the channel
    """
    payload = {
        "response_type": "in_channel" if in_channel else "ephemeral",
        "text": text,
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(response_url, json=payload, timeout=10)
    except Exception as exc:
        logger.error(f"Failed to send delayed Slack response | error={exc}")
