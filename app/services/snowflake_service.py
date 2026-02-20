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

# snowflake-connector-python only needed when MOCK_SNOWFLAKE=false
if not MOCK_SNOWFLAKE:
    try:
        import snowflake.connector as _sf_connector
    except ImportError as e:
        raise RuntimeError(
            "snowflake-connector-python is required when MOCK_SNOWFLAKE=false. "
            "Run: pip install snowflake-connector-python"
        ) from e
else:
    _sf_connector = None

from app.utils.logger import logger

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAFE_IDENTIFIER = re.compile(r"^\w+$")   # alphanumeric + underscore only


def _validate_identifier(value: str, label: str) -> None:
    """Block SQL injection on identifiers (usernames, roles, table names)."""
    if not _SAFE_IDENTIFIER.match(value):
        raise ValueError(
            f"Invalid {label}: '{value}'. Only letters, digits and _ allowed."
        )


def _generate_temp_password(length: int = 12) -> str:
    """
    Random password that meets Snowflake's default policy:
    >= 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special char.
    """
    upper   = random.choice(string.ascii_uppercase)
    lower   = random.choice(string.ascii_lowercase)
    digit   = random.choice(string.digits)
    special = random.choice("!@#$%^&*")
    rest    = random.choices(string.ascii_letters + string.digits, k=length - 4)
    pool    = list(upper + lower + digit + special) + rest
    random.shuffle(pool)
    return "".join(pool)


def _get_connection(user: str = None, password: str = None, role: str = None):
    """
    Returns a Snowflake connection.
    Defaults to the service account from .env.
    Pass user/password/role to connect as a different user (e.g. to verify login).
    """
    return _sf_connector.connect(
        account   = SNOWFLAKE_ACCOUNT,
        user      = user     or SNOWFLAKE_USER,
        password  = password or SNOWFLAKE_PASSWORD,
        warehouse = SNOWFLAKE_WAREHOUSE,
        database  = SNOWFLAKE_DATABASE,
        schema    = SNOWFLAKE_SCHEMA,
        role      = role     or SNOWFLAKE_ROLE,
    )


def _execute(sql: str, conn=None) -> list:
    """
    Runs one SQL statement, returns rows as list of dicts.
    Opens its own connection if none is passed.
    """
    own_conn = conn is None
    if own_conn:
        conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchall() or []
        return [dict(zip(cols, row)) for row in rows]
    finally:
        if own_conn:
            conn.close()


# ---------------------------------------------------------------------------
# USER MANAGEMENT
# ---------------------------------------------------------------------------

def onboard_user(username: str, role: str) -> dict:
    """
    Creates a new Snowflake user and grants them a role + CRUD permissions.

    SQL:
        CREATE USER "<username>" PASSWORD='...' MUST_CHANGE_PASSWORD=TRUE ...
        GRANT ROLE "<role>" TO USER "<username>"
        GRANT USAGE ON WAREHOUSE ... TO ROLE "<role>"
        GRANT USAGE ON DATABASE ... TO ROLE "<role>"
        GRANT USAGE ON SCHEMA ... TO ROLE "<role>"
        GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES ... TO ROLE "<role>"
    """
    _validate_identifier(username, "username")
    _validate_identifier(role, "role")

    temp_password = _generate_temp_password()

    if MOCK_SNOWFLAKE:
        logger.info(f"[MOCK] CREATE USER {username} | GRANT ROLE {role}")
        logger.info(f"[MOCK] GRANT CRUD on all tables to ROLE {role}")
    else:
        conn = _get_connection()
        try:
            # 1. Create user
            _execute(
                f'CREATE USER "{username}" '
                f"PASSWORD = '{temp_password}' "
                f"MUST_CHANGE_PASSWORD = TRUE "
                f'DEFAULT_ROLE = "{role}" '
                f"DEFAULT_WAREHOUSE = \"{SNOWFLAKE_WAREHOUSE}\" "
                f"COMMENT = 'Created via Slack integration'",
                conn
            )

            # 2. Ensure the role exists (create if not)
            _execute(f'CREATE ROLE IF NOT EXISTS "{role}"', conn)

            # 3. Grant role to user
            _execute(f'GRANT ROLE "{role}" TO USER "{username}"', conn)

            # 4. Grant warehouse access to role
            _execute(
                f'GRANT USAGE ON WAREHOUSE "{SNOWFLAKE_WAREHOUSE}" TO ROLE "{role}"',
                conn
            )

            # 5. Grant database access
            _execute(
                f'GRANT USAGE ON DATABASE "{SNOWFLAKE_DATABASE}" TO ROLE "{role}"',
                conn
            )

            # 6. Grant schema access
            _execute(
                f'GRANT USAGE ON SCHEMA "{SNOWFLAKE_DATABASE}"."{SNOWFLAKE_SCHEMA}" TO ROLE "{role}"',
                conn
            )

            # 7. Grant full CRUD on all existing tables in the schema
            _execute(
                f'GRANT SELECT, INSERT, UPDATE, DELETE '
                f'ON ALL TABLES IN SCHEMA "{SNOWFLAKE_DATABASE}"."{SNOWFLAKE_SCHEMA}" '
                f'TO ROLE "{role}"',
                conn
            )

            # 8. Grant CRUD on any future tables too
            _execute(
                f'GRANT SELECT, INSERT, UPDATE, DELETE '
                f'ON FUTURE TABLES IN SCHEMA "{SNOWFLAKE_DATABASE}"."{SNOWFLAKE_SCHEMA}" '
                f'TO ROLE "{role}"',
                conn
            )

            logger.info(
                f"Snowflake user onboarded | username={username} role={role}"
            )
        finally:
            conn.close()

    return {
        "username":      username,
        "role":          role,
        "temp_password": temp_password,
        "warehouse":     SNOWFLAKE_WAREHOUSE,
        "database":      SNOWFLAKE_DATABASE,
        "schema":        SNOWFLAKE_SCHEMA,
    }


def reset_password(username: str) -> dict:
    """
    Resets an existing Snowflake user's password.

    SQL:
        ALTER USER "<username>" SET PASSWORD='...' MUST_CHANGE_PASSWORD=TRUE
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


def list_users() -> list:
    """Returns all Snowflake users (name, created_on, default_role)."""
    if MOCK_SNOWFLAKE:
        logger.info("[MOCK] SHOW USERS")
        return [
            {"name": "JOHN",    "default_role": "ANALYST",   "created_on": "2026-02-20"},
            {"name": "JANE",    "default_role": "DEVELOPER",  "created_on": "2026-02-20"},
        ]
    rows = _execute("SHOW USERS")
    return [
        {
            "name":         r.get("name", ""),
            "default_role": r.get("default_role", ""),
            "created_on":   str(r.get("created_on", "")),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# CRUD OPERATIONS on Snowflake tables
# ---------------------------------------------------------------------------

def setup_demo_table() -> dict:
    """
    Creates a demo EMPLOYEES table in the configured database/schema.
    Useful for showing CRUD works end-to-end.

    SQL:
        CREATE TABLE IF NOT EXISTS EMPLOYEES (
            id          NUMBER AUTOINCREMENT PRIMARY KEY,
            name        VARCHAR(100),
            department  VARCHAR(100),
            salary      NUMBER,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    sql = (
        f'CREATE TABLE IF NOT EXISTS '
        f'"{SNOWFLAKE_DATABASE}"."{SNOWFLAKE_SCHEMA}"."EMPLOYEES" ('
        f'    id         NUMBER AUTOINCREMENT PRIMARY KEY,'
        f'    name       VARCHAR(100),'
        f'    department VARCHAR(100),'
        f'    salary     NUMBER,'
        f'    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        f')'
    )
    if MOCK_SNOWFLAKE:
        logger.info("[MOCK] CREATE TABLE EMPLOYEES")
        return {"message": "Demo table EMPLOYEES created (mock)"}

    _execute(sql)
    logger.info("Demo table EMPLOYEES created")
    return {"message": f"Table EMPLOYEES created in {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}"}


def create_record(name: str, department: str, salary: int) -> dict:
    """
    INSERT a row into EMPLOYEES table.
    Uses bind variables — safe from SQL injection.
    """
    if MOCK_SNOWFLAKE:
        logger.info(f"[MOCK] INSERT employee name={name} dept={department} salary={salary}")
        return {"message": f"Inserted employee '{name}' (mock)", "id": 1}

    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f'INSERT INTO "{SNOWFLAKE_DATABASE}"."{SNOWFLAKE_SCHEMA}"."EMPLOYEES" '
            f'(name, department, salary) VALUES (%s, %s, %s)',
            (name, department, salary)
        )
        logger.info(f"Record inserted | name={name} department={department}")
        return {"message": f"Employee '{name}' inserted successfully"}
    finally:
        conn.close()


def read_records(department: str = None) -> list:
    """
    SELECT rows from EMPLOYEES.
    Optionally filter by department (uses bind variable).
    """
    if MOCK_SNOWFLAKE:
        logger.info("[MOCK] SELECT from EMPLOYEES")
        return [
            {"ID": 1, "NAME": "John",  "DEPARTMENT": "Engineering", "SALARY": 80000},
            {"ID": 2, "NAME": "Jane",  "DEPARTMENT": "Marketing",   "SALARY": 75000},
        ]

    conn = _get_connection()
    try:
        cursor = conn.cursor()
        if department:
            cursor.execute(
                f'SELECT * FROM "{SNOWFLAKE_DATABASE}"."{SNOWFLAKE_SCHEMA}"."EMPLOYEES" '
                f'WHERE department = %s',
                (department,)
            )
        else:
            cursor.execute(
                f'SELECT * FROM "{SNOWFLAKE_DATABASE}"."{SNOWFLAKE_SCHEMA}"."EMPLOYEES"'
            )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def update_record(emp_id: int, name: str = None,
                  department: str = None, salary: int = None) -> dict:
    """
    UPDATE an EMPLOYEES row by id.
    Only updates the fields that are provided.
    """
    if MOCK_SNOWFLAKE:
        logger.info(f"[MOCK] UPDATE EMPLOYEES id={emp_id}")
        return {"message": f"Employee id={emp_id} updated (mock)"}

    updates = []
    values  = []
    if name:
        updates.append("name = %s");       values.append(name)
    if department:
        updates.append("department = %s"); values.append(department)
    if salary is not None:
        updates.append("salary = %s");     values.append(salary)

    if not updates:
        return {"message": "Nothing to update — provide name, department or salary"}

    values.append(emp_id)
    sql = (
        f'UPDATE "{SNOWFLAKE_DATABASE}"."{SNOWFLAKE_SCHEMA}"."EMPLOYEES" '
        f'SET {", ".join(updates)} WHERE id = %s'
    )

    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(values))
        logger.info(f"Record updated | id={emp_id}")
        return {"message": f"Employee id={emp_id} updated successfully"}
    finally:
        conn.close()


def delete_record(emp_id: int) -> dict:
    """
    DELETE an EMPLOYEES row by id.
    """
    if MOCK_SNOWFLAKE:
        logger.info(f"[MOCK] DELETE FROM EMPLOYEES id={emp_id}")
        return {"message": f"Employee id={emp_id} deleted (mock)"}

    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f'DELETE FROM "{SNOWFLAKE_DATABASE}"."{SNOWFLAKE_SCHEMA}"."EMPLOYEES" '
            f'WHERE id = %s',
            (emp_id,)
        )
        logger.info(f"Record deleted | id={emp_id}")
        return {"message": f"Employee id={emp_id} deleted successfully"}
    finally:
        conn.close()
