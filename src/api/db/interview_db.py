import sqlite3
from typing import List, Optional
from api.utils.db import get_new_db_connection
from api.models import NewInterviewCreate, NewInterviewRead, NewInterviewFeedbackCreate, NewInterviewFeedbackRead
from datetime import datetime

async def schedule_interview(interview: NewInterviewCreate) -> NewInterviewRead:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """INSERT INTO NEW_interviews
            (NEW_application_id, NEW_scheduled_time, NEW_duration_minutes, NEW_location_or_link)
            VALUES (?, ?, ?, ?)""",
            (
                interview.new_application_id,
                interview.new_scheduled_time,
                interview.new_duration_minutes,
                interview.new_location_or_link
            )
        )
        await conn.commit()
        new_id = cursor.lastrowid
        return NewInterviewRead(
            new_id=new_id,
            new_application_id=interview.new_application_id,
            new_scheduled_time=interview.new_scheduled_time,
            new_duration_minutes=interview.new_duration_minutes,
            new_location_or_link=interview.new_location_or_link,
            new_status="SCHEDULED"
        )

async def get_interview_details(interview_id: int) -> Optional[NewInterviewRead]:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """SELECT
                NEW_id, NEW_application_id, NEW_scheduled_time, NEW_duration_minutes, NEW_location_or_link, NEW_status
                FROM NEW_interviews WHERE NEW_id = ?""",
            (interview_id,)
        )
        row = await cursor.fetchone()
        if row:
            return NewInterviewRead(
                new_id=row[0],
                new_application_id=row[1],
                new_scheduled_time=datetime.fromisoformat(row[2]) if isinstance(row[2], str) else row[2],
                new_duration_minutes=row[3],
                new_location_or_link=row[4],
                new_status=row[5]
            )
        return None

async def add_interviewer(interview_id: int, user_id: int) -> bool:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        try:
            await cursor.execute(
                """INSERT INTO NEW_interviewers (NEW_interview_id, NEW_user_id) VALUES (?, ?)""",
                (interview_id, user_id)
            )
            await conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Interviewer already added or interview_id/user_id does not exist
            return False

async def submit_interview_feedback(feedback: NewInterviewFeedbackCreate) -> NewInterviewFeedbackRead:
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """INSERT INTO NEW_interview_feedback
            (NEW_interview_id, NEW_interviewer_user_id, NEW_overall_rating, NEW_feedback_for_candidate, NEW_internal_notes, NEW_hiring_decision)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                feedback.new_interview_id,
                feedback.new_interviewer_user_id,
                feedback.new_overall_rating,
                feedback.new_feedback_for_candidate,
                feedback.new_internal_notes,
                feedback.new_hiring_decision
            )
        )
        await conn.commit()
        new_id = cursor.lastrowid
        return NewInterviewFeedbackRead(
            new_id=new_id,
            new_interview_id=feedback.new_interview_id,
            new_interviewer_user_id=feedback.new_interviewer_user_id,
            new_overall_rating=feedback.new_overall_rating,
            new_feedback_for_candidate=feedback.new_feedback_for_candidate,
            new_internal_notes=feedback.new_internal_notes,
            new_hiring_decision=feedback.new_hiring_decision,
            new_submitted_at=datetime.now()
        )