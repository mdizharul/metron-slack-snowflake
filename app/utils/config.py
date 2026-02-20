import os
from dotenv import load_dotenv

load_dotenv()

# ── Slack ─────────────────────────────────────────────────────────────────────
SLACK_SIGNING_SECRET: str = os.getenv("SLACK_SIGNING_SECRET", "")
AUTHORIZED_SLACK_USER_IDS: list[str] = [
    uid.strip()
    for uid in os.getenv("AUTHORIZED_SLACK_USER_IDS", "").split(",")
    if uid.strip()
]

# ── Snowflake ─────────────────────────────────────────────────────────────────
SNOWFLAKE_ACCOUNT: str   = os.getenv("SNOWFLAKE_ACCOUNT", "")
SNOWFLAKE_USER: str      = os.getenv("SNOWFLAKE_USER", "")
SNOWFLAKE_PASSWORD: str  = os.getenv("SNOWFLAKE_PASSWORD", "")
SNOWFLAKE_WAREHOUSE: str = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
SNOWFLAKE_DATABASE: str  = os.getenv("SNOWFLAKE_DATABASE", "")
SNOWFLAKE_SCHEMA: str    = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
SNOWFLAKE_ROLE: str      = os.getenv("SNOWFLAKE_ROLE", "SYSADMIN")

# ── Server ────────────────────────────────────────────────────────────────────
PORT: int = int(os.getenv("PORT", 8000))

# ── Mock mode (for Postman testing without real Snowflake creds) ──────────────
MOCK_SNOWFLAKE: bool = os.getenv("MOCK_SNOWFLAKE", "true").lower() == "true"
