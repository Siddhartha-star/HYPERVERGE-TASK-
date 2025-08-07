import sqlite3
from typing import List, Optional
from api.utils.db import get_new_db_connection
from api.models import NewApplicationCreate, NewApplicationRead, NewJobPostingRead
from datetime import datetime
from api.db.job_posting_db import get_job_posting

async def create_application(conn: sqlite3.Connection, user_id: int, job_id: int) -> NewApplicationRead:
    cursor = await conn.cursor()
    await cursor.execute(
        """INSERT INTO NEW_applications
        (NEW_user_id, NEW_job_posting_id)
        VALUES (?, ?)""",
        (user_id, job_id)
    )
    new_id = cursor.lastrowid
    
    # Fetch the newly created application with job details for the response model
    created_app = await get_application_details_from_db(conn, new_id)
    if not created_app:
        raise Exception("Failed to retrieve newly created application.") # Should not happen
    return created_app

async def get_application_details_from_db(conn: sqlite3.Connection, application_id: int) -> Optional[NewApplicationRead]:
    cursor = await conn.cursor()
    await cursor.execute(
        """SELECT
            app.NEW_id, app.NEW_user_id, app.NEW_job_posting_id, app.NEW_status, app.NEW_applied_at, app.NEW_updated_at
            FROM NEW_applications app WHERE app.NEW_id = ?""",
        (application_id,)
    )
    row = await cursor.fetchone()
    if row:
        job_posting = await get_job_posting(conn, row[2]) # Fetch nested job posting
        if not job_posting:
            return None # Or raise an error, depending on desired behavior

        return NewApplicationRead(
            new_id=row[0],
            new_user_id=row[1],
            new_status=row[3],
            new_applied_at=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
            new_updated_at=datetime.fromisoformat(row[5]) if isinstance(row[5], str) else row[5],
            job_posting=job_posting
        )
    return None

async def get_application_for_user_and_job(user_id: int, job_posting_id: int) -> Optional[NewApplicationRead]:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """SELECT
                app.NEW_id, app.NEW_user_id, app.NEW_job_posting_id, app.NEW_status, app.NEW_applied_at, app.NEW_updated_at
                FROM NEW_applications app WHERE app.NEW_user_id = ? AND app.NEW_job_posting_id = ?""",
            (user_id, job_posting_id)
        )
        row = await cursor.fetchone()
        if row:
            job_posting = await get_job_posting(conn, row[2]) # Fetch nested job posting
            if not job_posting:
                return None

            return NewApplicationRead(
                new_id=row[0],
                new_user_id=row[1],
                new_status=row[3],
                new_applied_at=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
                new_updated_at=datetime.fromisoformat(row[5]) if isinstance(row[5], str) else row[5],
                job_posting=job_posting
            )
        return None

async def update_application_status(application_id: int, status: str) -> bool:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """UPDATE NEW_applications SET NEW_status = ?, NEW_updated_at = CURRENT_TIMESTAMP WHERE NEW_id = ?""",
            (status, application_id)
        )
        await conn.commit()
        return cursor.rowcount > 0

async def get_applications_for_job(job_posting_id: int) -> List[NewApplicationRead]:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """SELECT
                app.NEW_id, app.NEW_user_id, app.NEW_job_posting_id, app.NEW_status, app.NEW_applied_at, app.NEW_updated_at
                FROM NEW_applications app WHERE app.NEW_job_posting_id = ?""",
            (job_posting_id,)
        )
        rows = await cursor.fetchall()
        applications = []
        for row in rows:
            job_posting = await get_job_posting(conn, row[2])
            if job_posting:
                applications.append(NewApplicationRead(
                    new_id=row[0],
                    new_user_id=row[1],
                    new_status=row[3],
                    new_applied_at=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
                    new_updated_at=datetime.fromisoformat(row[5]) if isinstance(row[5], str) else row[5],
                    job_posting=job_posting
                ))
        return applications

async def get_applications_for_user(user_id: int) -> List[NewApplicationRead]:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """SELECT
                app.NEW_id, app.NEW_user_id, app.NEW_job_posting_id, app.NEW_status, app.NEW_applied_at, app.NEW_updated_at
                FROM NEW_applications app WHERE app.NEW_user_id = ?""",
            (user_id,)
        )
        rows = await cursor.fetchall()
        applications = []
        for row in rows:
            job_posting = await get_job_posting(conn, row[2])
            if job_posting:
                applications.append(NewApplicationRead(
                    new_id=row[0],
                    new_user_id=row[1],
                    new_status=row[3],
                    new_applied_at=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
                    new_updated_at=datetime.fromisoformat(row[5]) if isinstance(row[5], str) else row[5],
                    job_posting=job_posting
                ))
        return applications