from fastapi import HTTPException
from app.utils.config import AUTHORIZED_SLACK_USER_IDS
from app.utils.logger import logger


def authorize_user(user_id: str) -> None:
    """
    Checks the requesting Slack user is on the authorized allow-list.

    If AUTHORIZED_SLACK_USER_IDS is empty (not configured), all users are
    allowed — useful during local Postman testing.

    Raises HTTP 403 for unauthorized users.
    """
    if not AUTHORIZED_SLACK_USER_IDS:
        # No list configured → open access (dev/test mode)
        return

    if user_id not in AUTHORIZED_SLACK_USER_IDS:
        logger.warning(f"Unauthorized user attempted operation | user_id={user_id}")
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to perform Snowflake operations.",
        )
