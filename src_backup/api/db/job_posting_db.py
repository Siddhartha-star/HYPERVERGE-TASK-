import sqlite3
from typing import List, Optional
from api.utils.db import get_new_db_connection
from api.models import NewJobPostingCreate, NewJobPostingRead
from datetime import datetime

async def create_job_posting(job_posting: NewJobPostingCreate, posted_by_user_id: int) -> NewJobPostingRead:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """INSERT INTO NEW_job_postings
            (NEW_org_id, NEW_posted_by_user_id, NEW_title, NEW_description, NEW_location, NEW_job_type)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                job_posting.new_org_id,
                posted_by_user_id,
                job_posting.new_title,
                job_posting.new_description,
                job_posting.new_location,
                job_posting.new_job_type
            )
        )
        new_id = cursor.lastrowid

        # Link required skills to the job posting
        if job_posting.required_skills:
            await link_skills_to_job(conn, new_id, job_posting.required_skills)

        await conn.commit()
        return NewJobPostingRead(
            new_id=new_id,
            new_org_id=job_posting.new_org_id,
            new_posted_by_user_id=posted_by_user_id,
            new_title=job_posting.new_title,
            new_description=job_posting.new_description,
            new_location=job_posting.new_location,
            new_job_type=job_posting.new_job_type,
            new_status="OPEN", # Default status
            new_created_at=datetime.now(), # This will be updated by the DB, but for consistency
            required_skills=job_posting.required_skills
        )

async def link_skills_to_job(conn: sqlite3.Connection, job_id: int, skills_with_thresholds: List[dict]):
    cursor = await conn.cursor()
    for skill in skills_with_thresholds:
        await cursor.execute(
            """INSERT INTO NEW_job_required_skills (NEW_job_posting_id, NEW_skill_id, NEW_required_proficiency_threshold) VALUES (?, ?, ?)""",
            (job_id, skill["skill_id"], skill["threshold"])
        )

async def get_job_posting(conn: sqlite3.Connection, job_id: int) -> Optional[NewJobPostingRead]:
    cursor = await conn.cursor()
    await cursor.execute(
        """SELECT
            jp.NEW_id, jp.NEW_org_id, jp.NEW_posted_by_user_id, jp.NEW_title, jp.NEW_description,
            jp.NEW_location, jp.NEW_job_type, jp.NEW_status, jp.NEW_created_at,
            GROUP_CONCAT(jrs.NEW_skill_id || ':' || jrs.NEW_required_proficiency_threshold) AS required_skills_str
            FROM NEW_job_postings jp
            LEFT JOIN NEW_job_required_skills jrs ON jp.NEW_id = jrs.NEW_job_posting_id
            WHERE jp.NEW_id = ?
            GROUP BY jp.NEW_id""",
        (job_id,)
    )
    row = await cursor.fetchone()
    if row:
        required_skills = []
        if row[9]: # Check if required_skills_str is not None
            for skill_str in row[9].split(','):
                skill_id, threshold = map(int, skill_str.split(':'))
                required_skills.append({"skill_id": skill_id, "threshold": threshold})

        return NewJobPostingRead(
            new_id=row[0],
            new_org_id=row[1],
            new_posted_by_user_id=row[2],
            new_title=row[3],
            new_description=row[4],
            new_location=row[5],
            new_job_type=row[6],
            new_status=row[7],
            new_created_at=datetime.fromisoformat(row[8]) if isinstance(row[8], str) else row[8],
            required_skills=required_skills
        )
    return None

async def get_job_posting_by_id(job_posting_id: int) -> Optional[NewJobPostingRead]:
    async with get_new_db_connection() as conn:
        return await get_job_posting(conn, job_posting_id)

async def get_open_job_postings_for_org(org_id: int) -> List[NewJobPostingRead]:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """SELECT
                jp.NEW_id, jp.NEW_org_id, jp.NEW_posted_by_user_id, jp.NEW_title, jp.NEW_description,
                jp.NEW_location, jp.NEW_job_type, jp.NEW_status, jp.NEW_created_at,
                GROUP_CONCAT(jrs.NEW_skill_id || ':' || jrs.NEW_required_proficiency_threshold) AS required_skills_str
                FROM NEW_job_postings jp
                LEFT JOIN NEW_job_required_skills jrs ON jp.NEW_id = jrs.NEW_job_posting_id
                WHERE jp.NEW_org_id = ? AND jp.NEW_status = 'OPEN'
                GROUP BY jp.NEW_id""",
            (org_id,)
        )
        rows = await cursor.fetchall()
        jobs = []
        for row in rows:
            required_skills = []
            if row[9]:
                for skill_str in row[9].split(','):
                    skill_id, threshold = map(int, skill_str.split(':'))
                    required_skills.append({"skill_id": skill_id, "threshold": threshold})
            jobs.append(NewJobPostingRead(
                new_id=row[0],
                new_org_id=row[1],
                new_posted_by_user_id=row[2],
                new_title=row[3],
                new_description=row[4],
                new_location=row[5],
                new_job_type=row[6],
                new_status=row[7],
                new_created_at=datetime.fromisoformat(row[8]) if isinstance(row[8], str) else row[8],
                required_skills=required_skills
            ))
        return jobs

async def get_job_postings_for_org(org_id: int) -> List[NewJobPostingRead]:
    # Reusing the get_open_job_postings_for_org logic and removing the status filter for simplicity or creating a new function
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """SELECT
                jp.NEW_id, jp.NEW_org_id, jp.NEW_posted_by_user_id, jp.NEW_title, jp.NEW_description,
                jp.NEW_location, jp.NEW_job_type, jp.NEW_status, jp.NEW_created_at,
                GROUP_CONCAT(jrs.NEW_skill_id || ':' || jrs.NEW_required_proficiency_threshold) AS required_skills_str
                FROM NEW_job_postings jp
                LEFT JOIN NEW_job_required_skills jrs ON jp.NEW_id = jrs.NEW_job_posting_id
                WHERE jp.NEW_org_id = ?
                GROUP BY jp.NEW_id""",
            (org_id,)
        )
        rows = await cursor.fetchall()
        jobs = []
        for row in rows:
            required_skills = []
            if row[9]:
                for skill_str in row[9].split(','):
                    skill_id, threshold = map(int, skill_str.split(':'))
                    required_skills.append({"skill_id": skill_id, "threshold": threshold})
            jobs.append(NewJobPostingRead(
                new_id=row[0],
                new_org_id=row[1],
                new_posted_by_user_id=row[2],
                new_title=row[3],
                new_description=row[4],
                new_location=row[5],
                new_job_type=row[6],
                new_status=row[7],
                new_created_at=datetime.fromisoformat(row[8]) if isinstance(row[8], str) else row[8],
                required_skills=required_skills
            ))
        return jobs

async def update_job_posting_status(job_posting_id: int, status: str) -> bool:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """UPDATE NEW_job_postings SET NEW_status = ? WHERE NEW_id = ?""",
            (status, job_posting_id)
        )
        await conn.commit()
        return cursor.rowcount > 0