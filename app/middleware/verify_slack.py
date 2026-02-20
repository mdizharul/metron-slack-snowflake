import hashlib
import hmac
import time

from fastapi import Request, HTTPException
from app.utils.config import SLACK_SIGNING_SECRET
from app.utils.logger import logger


async def verify_slack_signature(request: Request) -> bytes:
    """
    Validates every inbound request came from Slack.

    Slack signs requests with HMAC-SHA256 using your Signing Secret.
    Steps:
      1. Read the raw body (needed to recompute the signature).
      2. Check the timestamp is within 5 minutes  →  replay-attack prevention.
      3. Recompute expected signature and compare with timingSafeEqual.

    Returns the raw body bytes so the route can parse it.
    Raises HTTP 401 on any failure.
    """
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    slack_sig = request.headers.get("X-Slack-Signature", "")

    if not timestamp or not slack_sig:
        logger.warning("Missing Slack signature headers")
        raise HTTPException(status_code=401, detail="Unauthorized – missing headers")

    # Reject stale requests (> 5 minutes old)
    if abs(time.time() - int(timestamp)) > 300:
        logger.warning("Slack request timestamp too old", extra={"timestamp": timestamp})
        raise HTTPException(status_code=401, detail="Unauthorized – request expired")

    raw_body: bytes = await request.body()
    base_string = f"v0:{timestamp}:{raw_body.decode('utf-8')}"

    expected_sig = (
        "v0="
        + hmac.new(
            SLACK_SIGNING_SECRET.encode(),
            base_string.encode(),
            hashlib.sha256,
        ).hexdigest()
    )

    if not hmac.compare_digest(expected_sig, slack_sig):
        logger.warning("Slack signature mismatch")
        raise HTTPException(status_code=401, detail="Unauthorized – invalid signature")

    return raw_body
