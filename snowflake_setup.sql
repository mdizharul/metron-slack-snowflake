-- ============================================================
-- Run this ENTIRE script in Snowflake Worksheet as ACCOUNTADMIN
-- Select All (Ctrl+A) then click Run
-- ============================================================

USE ROLE ACCOUNTADMIN;

-- 1. Create or fix service account
CREATE USER IF NOT EXISTS slack_svc_account
    PASSWORD = 'SlackBot@2024!'
    DEFAULT_ROLE = ACCOUNTADMIN
    DEFAULT_WAREHOUSE = 'COMPUTE_WH'
    MUST_CHANGE_PASSWORD = FALSE
    COMMENT = 'Service account for Slack-Snowflake integration';

-- 2. Grant ACCOUNTADMIN (needed to CREATE USER)
GRANT ROLE ACCOUNTADMIN TO USER slack_svc_account;

-- 3. Create the database and schema
CREATE DATABASE IF NOT EXISTS SNOWFLAKE_LEARNING_DB;
CREATE SCHEMA IF NOT EXISTS SNOWFLAKE_LEARNING_DB.PUBLIC;

-- 4. Create EMPLOYEES table for CRUD demo
CREATE TABLE IF NOT EXISTS SNOWFLAKE_LEARNING_DB.PUBLIC.EMPLOYEES (
    id         NUMBER AUTOINCREMENT PRIMARY KEY,
    name       VARCHAR(100),
    department VARCHAR(100),
    salary     NUMBER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Verify everything
SELECT 'Service account' as check_item, 'OK' as status
WHERE EXISTS (SELECT 1 FROM SNOWFLAKE.ACCOUNT_USAGE.USERS WHERE NAME = 'SLACK_SVC_ACCOUNT');

SHOW TABLES IN SNOWFLAKE_LEARNING_DB.PUBLIC;

-- Done!
SELECT 'Setup complete!' as message;
