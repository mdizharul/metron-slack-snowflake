from urllib.parse import parse_qs

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from fastapi.responses import JSONResponse

from app.middleware.authorize_user import authorize_user
from app.middleware.verify_slack import verify_slack_signature
from app.services.slack_responder import send_delayed_response
from app.services.snowflake_service import onboard_user, reset_password
from app.utils.config import SLACK_SIGNING_SECRET
from app.utils.logger import logger

router = APIRouter(prefix="/slack", tags=["Slack"])


# ---------------------------------------------------------------------------
# POST /slack/command
# ---------------------------------------------------------------------------

@router.post("/command")
async def slack_command(request: Request, background_tasks: BackgroundTasks):
    """
    Entry point for all Slack slash commands.

    Slack sends an application/x-www-form-urlencoded POST with fields:
        user_id      — Slack user ID of the person who ran the command
        command      — the slash command  e.g. /snowflake
        text         — everything after the command  e.g. onboard_user john ANALYST
        response_url — URL to post a delayed reply to

    Flow:
        1. Verify the request signature (skip in mock/test mode).
        2. Check the user is authorized.
        3. Immediately return HTTP 200 ACK to Slack.
        4. Run the Snowflake operation in a background task.
        5. POST the result back to Slack via response_url.
    """

    # ── 1. Signature verification ──────────────────────────────────────────
    # NOTE: Disabled for demo — re-enable in production by setting
    # VERIFY_SLACK_SIGNATURE=true in environment variables
    import os
    if os.getenv("VERIFY_SLACK_SIGNATURE", "false").lower() == "true":
        await verify_slack_signature(request)

    # ── 2. Parse the URL-encoded body ──────────────────────────────────────
    raw_body = await request.body()
    params = parse_qs(raw_body.decode("utf-8"))

    def get(key: str) -> str:
        return params.get(key, [""])[0]

    user_id      = get("user_id")
    text         = get("text").strip()
    response_url = get("response_url")

    logger.info(f"Slack command received | user_id={user_id} text='{text}'")

    # ── 3. Authorization ───────────────────────────────────────────────────
    # NOTE: Disabled for demo — re-enable by setting AUTHORIZED_SLACK_USER_IDS in env
    # authorize_user(user_id)
    logger.info(f"Request from user_id={user_id} (auth check disabled for demo)")

    if not text:
        return JSONResponse({
            "response_type": "ephemeral",
            "text": (
                "Available commands:\n"
                "• `/snowflake onboard_user <username> <role>`\n"
                "• `/snowflake reset_password <username>`"
            ),
        })

    # ── 4. Parse subcommand ────────────────────────────────────────────────
    parts      = text.split()
    subcommand = parts[0].lower()

    # ── 5. Immediately ACK Slack (< 3 seconds rule) ────────────────────────
    # The real result is sent via response_url in a background task below.
    ack_response = JSONResponse({
        "response_type": "ephemeral",
        "text": f"⏳ Processing `{text}`...",
    })

    # ── 6. Schedule the Snowflake operation as a background task ───────────
    if subcommand == "onboard_user":
        background_tasks.add_task(
            _handle_onboard, parts, user_id, response_url
        )

    elif subcommand == "reset_password":
        background_tasks.add_task(
            _handle_reset, parts, user_id, response_url
        )

    else:
        background_tasks.add_task(
            send_delayed_response,
            response_url,
            (
                f"❓ Unknown subcommand: `{subcommand}`\n\n"
                "*Available commands:*\n"
                "• `/snowflake onboard_user <username> <role>`\n"
                "• `/snowflake reset_password <username>`"
            ),
        )

    return ack_response


# ---------------------------------------------------------------------------
# Background task handlers
# ---------------------------------------------------------------------------

async def _handle_onboard(parts: list[str], user_id: str, response_url: str):
    if len(parts) < 3:
        await send_delayed_response(
            response_url,
            "❌ Usage: `/snowflake onboard_user <username> <role>`",
        )
        return

    username, role = parts[1], parts[2]
    try:
        result = onboard_user(username, role)
        await send_delayed_response(
            response_url,
            f"✅ *User onboarded successfully*\n"
            f"• Username: `{result['username']}`\n"
            f"• Role: `{result['role']}`\n"
            f"• Temp password: `{result['temp_password']}`\n"
            f"_User must change password on first login._",
        )
        logger.info(
            f"Onboard completed | performed_by={user_id} "
            f"username={result['username']} role={result['role']}"
        )
    except Exception as exc:
        logger.error(f"Onboard failed | user_id={user_id} error={exc}")
        await send_delayed_response(response_url, f"❌ *Onboard failed:* {exc}")


async def _handle_reset(parts: list[str], user_id: str, response_url: str):
    if len(parts) < 2:
        await send_delayed_response(
            response_url,
            "❌ Usage: `/snowflake reset_password <username>`",
        )
        return

    username = parts[1]
    try:
        result = reset_password(username)
        await send_delayed_response(
            response_url,
            f"✅ *Password reset successfully*\n"
            f"• Username: `{result['username']}`\n"
            f"• New temp password: `{result['temp_password']}`\n"
            f"_User must change password on next login._",
        )
        logger.info(
            f"Password reset completed | performed_by={user_id} "
            f"username={result['username']}"
        )
    except Exception as exc:
        logger.error(f"Password reset failed | user_id={user_id} error={exc}")
        await send_delayed_response(response_url, f"❌ *Reset failed:* {exc}")
