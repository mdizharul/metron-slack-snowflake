# Metron Security — Slack–Snowflake Integration

Slack slash commands for Snowflake user operations, built with Python + FastAPI.

---

## Architecture

```
Slack User types:  /snowflake onboard_user john ANALYST
                              │
                    Slack API (HTTPS POST)
                              │
                    POST /slack/command
                              │
                   ┌──────────▼──────────┐
                   │  verify_slack.py    │  HMAC-SHA256 signature check
                   │  authorize_user.py  │  Allow-list check
                   │  slack.py (route)   │  Parse subcommand
                   └──────────┬──────────┘
                              │ HTTP 200 ACK  (immediate, < 3s)
                              │
                   ┌──────────▼──────────┐
                   │ snowflake_service   │  Background task
                   │  onboard_user()     │  CREATE USER + GRANT ROLE
                   │  reset_password()   │  ALTER USER SET PASSWORD
                   └──────────┬──────────┘
                              │
                   slack_responder.py
                   POST to response_url  →  Slack channel (ephemeral)
```

---

## Slash Commands

| Command | Action |
|---------|--------|
| `/snowflake onboard_user <username> <role>` | Creates user + grants role |
| `/snowflake reset_password <username>` | Resets password to temporary one |

---

## Quickstart

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env       # Windows
# cp .env.example .env       # Mac/Linux
# Edit .env — set MOCK_SNOWFLAKE=true for local testing

# 4. Run the server
python main.py
# Server starts at http://localhost:8000

# 5. Interactive API docs
# Open http://localhost:8000/docs
```

---

## Postman Testing (no Slack or Snowflake needed)

Create a POST request:
- **URL:** `http://localhost:8000/slack/command`
- **Body:** `x-www-form-urlencoded`

| Key | Value |
|-----|-------|
| `user_id` | `U12345678` |
| `text` | `onboard_user john ANALYST` |
| `response_url` | `https://httpbin.org/post` |

Check `https://httpbin.org/post` in your browser to see the Snowflake result.

---

## Security Design

| Concern | Solution |
|---------|----------|
| Request authenticity | HMAC-SHA256 (Slack Signing Secret) |
| Replay attacks | Reject requests > 5 min old |
| Authorization | Env-configured Slack user ID allow-list |
| SQL injection | Regex validation `^\w+$` on all identifiers |
| Credentials | Service account; `.env` never committed |
| Audit trail | All operations logged to `logs/audit.log` |
