from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.snowflake_service import (
    setup_demo_table,
    create_record,
    read_records,
    update_record,
    delete_record,
    list_users,
    onboard_user,
    reset_password,
)
from app.utils.logger import logger

router = APIRouter(prefix="/snowflake", tags=["Snowflake CRUD"])


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------

class OnboardRequest(BaseModel):
    username: str
    role:     str

class ResetPasswordRequest(BaseModel):
    username: str

class CreateEmployeeRequest(BaseModel):
    name:       str
    department: str
    salary:     int

class UpdateEmployeeRequest(BaseModel):
    name:       Optional[str] = None
    department: Optional[str] = None
    salary:     Optional[int] = None


# ---------------------------------------------------------------------------
# USER MANAGEMENT  (direct REST — no Slack needed)
# ---------------------------------------------------------------------------

@router.post("/users/onboard", summary="Create a new Snowflake user + grant role + CRUD permissions")
def api_onboard_user(body: OnboardRequest):
    """
    Creates a Snowflake user, assigns the role, and grants CRUD access
    on all tables in the configured database/schema.

    Returns the temporary password — user must change on first login.
    """
    try:
        result = onboard_user(body.username, body.role)
        logger.info(f"API onboard | username={body.username} role={body.role}")
        return {
            "status":  "success",
            "message": f"User '{body.username}' created and ready to login to Snowflake",
            "data":    result,
            "login_instructions": {
                "url":          "https://app.snowflake.com",
                "account":      "NRTBATY-MS68950",
                "username":     result["username"],
                "temp_password": result["temp_password"],
                "note":         "User must change password on first login"
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Onboard failed | error={e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/reset-password", summary="Reset a Snowflake user's password")
def api_reset_password(body: ResetPasswordRequest):
    """Resets the user's password to a new temporary one."""
    try:
        result = reset_password(body.username)
        return {
            "status":  "success",
            "message": f"Password reset for '{body.username}'",
            "data":    result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Password reset failed | error={e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users", summary="List all Snowflake users")
def api_list_users():
    """Returns all users in the Snowflake account."""
    try:
        users = list_users()
        return {"status": "success", "count": len(users), "data": users}
    except Exception as e:
        logger.error(f"List users failed | error={e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# SETUP — Create demo table
# ---------------------------------------------------------------------------

@router.post("/setup", summary="Create the EMPLOYEES demo table")
def api_setup():
    """
    Creates an EMPLOYEES table in Snowflake for CRUD demos.
    Run this ONCE before testing create/read/update/delete.
    """
    try:
        result = setup_demo_table()
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Setup failed | error={e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# CRUD — EMPLOYEES table
# ---------------------------------------------------------------------------

@router.post("/employees", summary="INSERT — Create a new employee record")
def api_create_employee(body: CreateEmployeeRequest):
    """
    Inserts a new row into the EMPLOYEES table.
    Uses parameterized queries — safe from SQL injection.
    """
    try:
        result = create_record(body.name, body.department, body.salary)
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Insert failed | error={e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employees", summary="SELECT — Read all employees (optional dept filter)")
def api_read_employees(department: Optional[str] = None):
    """
    Fetches all rows from EMPLOYEES.
    Pass ?department=Engineering to filter by department.
    """
    try:
        rows = read_records(department)
        return {"status": "success", "count": len(rows), "data": rows}
    except Exception as e:
        logger.error(f"Select failed | error={e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/employees/{emp_id}", summary="UPDATE — Update an employee record")
def api_update_employee(emp_id: int, body: UpdateEmployeeRequest):
    """
    Updates name, department, or salary for a given employee ID.
    Only the fields you provide will be updated.
    """
    try:
        result = update_record(emp_id, body.name, body.department, body.salary)
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Update failed | error={e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/employees/{emp_id}", summary="DELETE — Delete an employee record")
def api_delete_employee(emp_id: int):
    """Deletes the employee row with the given ID."""
    try:
        result = delete_record(emp_id)
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Delete failed | error={e}")
        raise HTTPException(status_code=500, detail=str(e))
