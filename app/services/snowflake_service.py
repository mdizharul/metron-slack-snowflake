import random
import re
import string

from app.utils.config import (
    MOCK_SNOWFLAKE,
    SNOWFLAKE_ACCOUNT,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_PASSWORD,
    SNOWFLAKE_ROLE,
    SNOWFLAKE_SCHEMA,
    SNOWFLAKE_USER,
    SNOWFLAKE_WAREHOUSE,
)

# snowflake-connector-python is only needed when MOCK_SNOWFLAKE=false.
# We do a lazy import so the server starts cleanly even without the package.
if not MOCK_SNOWFLAKE:
    try:
        import snowflake.connector as _sf_connector
    except ImportError as e:
        raise RuntimeError(
            "snowflake-connector-python is required when MOCK_SNOWFLAKE=false. "
            "Run: pip install snowflake-connector-python"
        ) from e
else:
    _sf_connector = None  # not needed in mock mode
from app.utils.logger import logger

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAFE_IDENTIFIER = re.compile(r"^\w+$")  # alphanumeric + underscore only


def _validate_identifier(value: str, label: str) -> None:
    """Prevent SQL injection in identifiers (usernames, roles)."""
    if not _SAFE_IDENTIFIER.match(value):
        raise ValueError(f"Invalid {label}: '{value}'. Only letters, digits and _ allowed.")


def _generate_temp_password(length: int = 12) -> str:
    """
    Generates a random password that satisfies Snowflake's default policy:
    ≥ 8 chars, at least one uppercase, lowercase, digit and special character.
    """
    upper   = random.choice(string.ascii_uppercase)
    lower   = random.choice(string.ascii_lowercase)
    digit   = random.choice(string.digits)
    special = random.choice("!@#$%^&*")
    rest    = random.choices(string.ascii_letters + string.digits, k=length - 4)
    pool    = list(upper + lower + digit + special) + rest
    random.shuffle(pool)
    return "".join(pool)


def _get_connection():
    return _sf_connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
        role=SNOWFLAKE_ROLE,
    )


def _execute(sql: str) -> list:
    """Opens a connection, runs one SQL statement, closes connection."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public operations
# ---------------------------------------------------------------------------

def onboard_user(username: str, role: str) -> dict:
    """
    Creates a new Snowflake user and grants them the specified role.

    SQL executed:
        CREATE USER "<username>"
            PASSWORD = '<temp>'
            MUST_CHANGE_PASSWORD = TRUE
            DEFAULT_ROLE = "<role>";

        GRANT ROLE "<role>" TO USER "<username>";
    """
    _validate_identifier(username, "username")
    _validate_identifier(role, "role")

    temp_password = _generate_temp_password()

    if MOCK_SNOWFLAKE:
        logger.info(f"[MOCK] CREATE USER {username} WITH ROLE {role}")
    else:
        _execute(
            f'CREATE USER "{username}" '
            f"PASSWORD = '{temp_password}' "
            f"MUST_CHANGE_PASSWORD = TRUE "
            f'DEFAULT_ROLE = "{role}" '
            f"COMMENT = 'Created via Slack integration'"
        )
        _execute(f'GRANT ROLE "{role}" TO USER "{username}"')
        logger.info(f"Snowflake user onboarded | username={username} role={role}")

    return {"username": username, "role": role, "temp_password": temp_password}


def reset_password(username: str) -> dict:
    """
    Resets an existing Snowflake user's password to a new temporary one.

    SQL executed:
        ALTER USER "<username>"
            SET PASSWORD = '<temp>'
                MUST_CHANGE_PASSWORD = TRUE;
    """
    _validate_identifier(username, "username")

    temp_password = _generate_temp_password()

    if MOCK_SNOWFLAKE:
        logger.info(f"[MOCK] ALTER USER {username} RESET PASSWORD")
    else:
        _execute(
            f'ALTER USER "{username}" '
            f"SET PASSWORD = '{temp_password}' "
            f"MUST_CHANGE_PASSWORD = TRUE"
        )
        logger.info(f"Snowflake password reset | username={username}")

    return {"username": username, "temp_password": temp_password}
