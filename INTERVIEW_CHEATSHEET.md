# INTERVIEW CHEAT SHEET — Slack Snowflake Integration

---

## SERVER
Start: cd C:\Users\MAnsari\Downloads\Metron-security && python main.py
URL:   http://localhost:8000
Docs:  http://localhost:8000/docs

---

## ALL POSTMAN API CALLS

### HEALTH
GET http://localhost:8000/health

### SETUP (run once)
POST http://localhost:8000/snowflake/setup
Body: none

### ONBOARD USER (creates real Snowflake user)
POST http://localhost:8000/snowflake/users/onboard
Body (JSON):
{
  "username": "demo_user",
  "role": "ANALYST"
}

### RESET PASSWORD
POST http://localhost:8000/snowflake/users/reset-password
Body (JSON):
{
  "username": "demo_user"
}

### LIST ALL SNOWFLAKE USERS
GET http://localhost:8000/snowflake/users

### CREATE EMPLOYEE (INSERT)
POST http://localhost:8000/snowflake/employees
Body (JSON):
{
  "name": "Alice Smith",
  "department": "Engineering",
  "salary": 85000
}

### READ ALL EMPLOYEES (SELECT)
GET http://localhost:8000/snowflake/employees

### READ WITH FILTER
GET http://localhost:8000/snowflake/employees?department=Engineering

### UPDATE EMPLOYEE
PUT http://localhost:8000/snowflake/employees/1
Body (JSON):
{
  "salary": 95000,
  "department": "Senior Engineering"
}

### DELETE EMPLOYEE
DELETE http://localhost:8000/snowflake/employees/1

---

## SNOWFLAKE VERIFY QUERIES (run in Snowflake Worksheet)

-- Check user was created
SHOW USERS LIKE 'DEMO_USER';

-- Check employees table
SELECT * FROM SNOWFLAKE_LEARNING_DB.PUBLIC.EMPLOYEES;

-- Check all tables
SHOW TABLES IN SNOWFLAKE_LEARNING_DB.PUBLIC;

---

## PROJECT STRUCTURE

main.py                        ← boots FastAPI server on port 8000
app/
  routes/
    slack.py                   ← POST /slack/command (Slack slash commands)
    crud.py                    ← All REST APIs (/snowflake/...)
  middleware/
    verify_slack.py            ← HMAC-SHA256 Slack signature check
    authorize_user.py          ← User allow-list check
  services/
    snowflake_service.py       ← All Snowflake SQL operations
    slack_responder.py         ← Posts results back to Slack
  utils/
    config.py                  ← Reads .env variables
    logger.py                  ← Writes audit.log
logs/
  audit.log                    ← Every action logged here

---

## CODE FLOW (say this in interview)

1. Postman/Slack sends POST to /snowflake/users/onboard
2. verify_slack.py checks HMAC signature (Slack only)
3. authorize_user.py checks user ID is in allow-list
4. crud.py route receives request, validates with Pydantic
5. snowflake_service.py runs SQL:
   - CREATE USER
   - CREATE ROLE IF NOT EXISTS
   - GRANT ROLE TO USER
   - GRANT USAGE ON WAREHOUSE
   - GRANT USAGE ON DATABASE
   - GRANT USAGE ON SCHEMA
   - GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES
6. logger.py writes to audit.log
7. Response returned to caller

---

## KEY INTERVIEW ANSWERS

Q: Where are your APIs?
A: app/routes/crud.py — 9 endpoints with Pydantic validation

Q: Where does Snowflake SQL run?
A: app/services/snowflake_service.py

Q: How do you prevent SQL injection?
A: Regex ^\w+$ on identifiers, bind params %s on values

Q: Why FastAPI over Flask?
A: Async/background tasks, auto Swagger docs, Pydantic validation

Q: Why background tasks?
A: Slack needs HTTP 200 in under 3 seconds. Snowflake is slow.
   We ACK immediately, run SQL in background, POST result to response_url

Q: How is Slack request verified?
A: HMAC-SHA256 with Signing Secret + 5-min timestamp replay check

Q: How is authorization done?
A: Allow-list of Slack user IDs in .env (AUTHORIZED_SLACK_USER_IDS)

Q: How is it audited?
A: logs/audit.log — every operation logged with user ID + timestamp

Q: What would you improve in production?
A: Connection pooling, DB-backed auth list, least-privilege role,
   rate limiting, send temp password via DM not channel

---

## SNOWFLAKE ACCOUNT DETAILS
Account:   nrtbaty-ms68950
Login URL: https://app.snowflake.com
DB:        SNOWFLAKE_LEARNING_DB
Schema:    PUBLIC
Table:     EMPLOYEES
Warehouse: COMPUTE_WH
Svc User:  slack_svc_account

---

## SLACK DETAILS
Workspace:   slack-snowflake-integration
Slash cmd:   /snowflake
Member ID:   U0AFY2MF799
Signing sec: (in .env)

---

## SLASH COMMANDS (when Slack is connected)
/snowflake onboard_user john ANALYST
/snowflake reset_password john
