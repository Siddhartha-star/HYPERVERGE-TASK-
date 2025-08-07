import sqlite3
from typing import List, Optional
from api.utils.db import get_new_db_connection
from api.models import NewSkillCreate, NewSkillRead, NewCandidateProfileUpdate, NewCandidateProfileRead

async def create_skill(skill: NewSkillCreate) -> NewSkillRead:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """INSERT INTO NEW_skills (NEW_name, NEW_category) VALUES (?, ?)""",
            (skill.new_name, skill.new_category)
        )
        await conn.commit()
        new_id = cursor.lastrowid
        return NewSkillRead(new_id=new_id, new_name=skill.new_name, new_category=skill.new_category)

async def get_skill_by_id(skill_id: int) -> Optional[NewSkillRead]:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """SELECT NEW_id, NEW_name, NEW_category FROM NEW_skills WHERE NEW_id = ?""",
            (skill_id,)
        )
        row = await cursor.fetchone()
        if row:
            return NewSkillRead(new_id=row[0], new_name=row[1], new_category=row[2])
        return None

async def get_all_skills() -> List[NewSkillRead]:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """SELECT NEW_id, NEW_name, NEW_category FROM NEW_skills"""
        )
        rows = await cursor.fetchall()
        return [NewSkillRead(new_id=row[0], new_name=row[1], new_category=row[2]) for row in rows]

async def create_or_update_candidate_skill(
    user_id: int, skill_id: int, proficiency_score: int, verification_source_task_id: Optional[int] = None
):
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """INSERT OR REPLACE INTO NEW_candidate_skills
            (NEW_user_id, NEW_skill_id, NEW_proficiency_score, NEW_verification_source_task_id, NEW_last_verified_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (user_id, skill_id, proficiency_score, verification_source_task_id)
        )
        await conn.commit()