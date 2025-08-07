from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone, timedelta
from api.config import (
    users_table_name,
    cohorts_table_name,
    user_cohorts_table_name,
    organizations_table_name,
    group_role_learner,
    courses_table_name,
    chat_history_table_name,
    questions_table_name,
    course_tasks_table_name,
    course_cohorts_table_name,
    task_completions_table_name,
    user_organizations_table_name,
)
from api.slack import send_slack_notification_for_new_user
from api.models import UserCohort
from api.utils import generate_random_color, get_date_from_str
from api.utils.db import execute_db_operation, get_new_db_connection
from api.models import NewCandidateProfileRead, NewCandidateProfileUpdate
import sqlite3
from api.models import User


async def update_user_email(email_1: str, email_2: str) -> None:
    await execute_db_operation(
        f"UPDATE {users_table_name} SET email = ? WHERE email = ?",
        (email_2, email_1),
    )


async def get_user_organizations(user_id: int):
    user_organizations = await execute_db_operation(
        f"""SELECT uo.org_id, o.name, uo.role, o.openai_api_key, o.openai_free_trial
        FROM {user_organizations_table_name} uo
        JOIN organizations o ON uo.org_id = o.id 
        WHERE uo.user_id = ? ORDER BY uo.id DESC""",
        (user_id,),
        fetch_all=True,
    )

    return [
        {
            "id": user_organization[0],
            "name": user_organization[1],
            "role": user_organization[2],
            "openai_api_key": user_organization[3],
            "openai_free_trial": user_organization[4],
        }
        for user_organization in user_organizations
    ]


async def get_user_organizations_with_roles(user_id: int, org_id: int) -> Dict[int, str]:
    """Gets the user's role(s) within a specific organization."""
    ### TODO: Implement this function
    # This function is a placeholder and should be implemented based on your
    # application's logic for determining user roles within an organization.
    # For example, it might query a user_organizations table.
    # For now, it returns a dummy dictionary.
    # In a real scenario, you'd fetch roles from the database.
    return {org_id: "ADMIN"} # Dummy data, replace with actual DB query


async def get_user_role_in_org(conn: sqlite3.Connection, user_id: int, org_id: int) -> Optional[str]:
    cursor = await conn.cursor()
    await cursor.execute(
        f"""SELECT role FROM {user_organizations_table_name} WHERE user_id = ? AND org_id = ?""",
        (user_id, org_id)
    )
    result = await cursor.fetchone()
    return result[0] if result else None


async def get_user_org_cohorts(user_id: int, org_id: int) -> List[UserCohort]:
    """
    Get all the cohorts in the organization that the user is a member in
    """
    cohorts = await execute_db_operation(
        f"""SELECT c.id, c.name, uc.role, uc.joined_at
            FROM {cohorts_table_name} c
            JOIN {user_cohorts_table_name} uc ON c.id = uc.cohort_id
            WHERE uc.user_id = ? AND c.org_id = ?""",
        (user_id, org_id),
        fetch_all=True,
    )

    if not cohorts:
        return []

    return [
        {
            "id": cohort[0],
            "name": cohort[1],
            "role": cohort[2],
            "joined_at": cohort[3],
        }
        for cohort in cohorts
    ]


def drop_users_table():
    execute_db_operation(f"DELETE FROM {users_table_name}")
    execute_db_operation(f"DROP TABLE IF EXISTS {users_table_name}")


def convert_user_db_to_dict(user: Tuple) -> Dict:
    if not user:
        return

    return {
        "id": user[0],
        "email": user[1],
        "first_name": user[2],
        "middle_name": user[3],
        "last_name": user[4],
        "default_dp_color": user[5],
        "created_at": user[6],
    }


async def insert_or_return_user(
    cursor,
    email: str,
    given_name: str = None,
    family_name: str = None,
):
    """
    Inserts a new user or returns an existing user.

    Args:
        email: The user's email address.
        given_name: The user's given name (first and middle names).
        family_name: The user's family name (last name).
        cursor: An existing database cursor

    Returns:
        A tuple containing the user data and a boolean indicating if the user is new.

    Raises:
        Any exception raised by the database operations.
    """

    if given_name is None:
        first_name = None
        middle_name = None
    else:
        given_name_parts = given_name.split(" ")
        first_name = given_name_parts[0]
        middle_name = " ".join(given_name_parts[1:])
        if not middle_name:
            middle_name = None

    # if user exists, no need to do anything, just return the user
    await cursor.execute(
        f"""SELECT * FROM {users_table_name} WHERE email = ?""",
        (email,),
    )

    user = await cursor.fetchone()

    if user:
        user = convert_user_db_to_dict(user)
        if user["first_name"] is None and first_name:
            user = await update_user(
                cursor,
                user["id"],
                first_name,
                middle_name,
                family_name,
                user["default_dp_color"],
            )

        return user, False # Existing user

    # create a new user
    color = generate_random_color()
    await cursor.execute(
        f"""
        INSERT INTO {users_table_name} (email, default_dp_color, first_name, middle_name, last_name)
        VALUES (?, ?, ?, ?, ?)
    """,
        (email, color, first_name, middle_name, family_name),
    )

    await cursor.execute(
        f"""SELECT * FROM {users_table_name} WHERE email = ?""",
        (email,),
    )

    user = convert_user_db_to_dict(await cursor.fetchone())

    # Send Slack notification for new user
    await send_slack_notification_for_new_user(user)

    return user, True # New user


async def update_user(
    cursor,
    user_id: str,
    first_name: str,
    middle_name: str,
    last_name: str,
    default_dp_color: str,
):
    await cursor.execute(
        f"UPDATE {users_table_name} SET first_name = ?, middle_name = ?, last_name = ?, default_dp_color = ? WHERE id = ?",
        (first_name, middle_name, last_name, default_dp_color, user_id),
    )

    user = await get_user_by_id(user_id)
    return user


async def get_all_users():
    users = await execute_db_operation(
        f"SELECT * FROM {users_table_name}",
        fetch_all=True,
    )

    return [convert_user_db_to_dict(user) for user in users]


async def get_user_by_email(email: str) -> User | None:
    user = await execute_db_operation(
        f"SELECT * FROM {users_table_name} WHERE email = ?", (email,), fetch_one=True
    )

    return convert_user_db_to_dict(user)


async def get_user_by_id(user_id: str) -> Dict:
    user = await execute_db_operation(
        f"SELECT * FROM {users_table_name} WHERE id = ?", (user_id,), fetch_one=True
    )

    return convert_user_db_to_dict(user)


async def get_user_cohorts(user_id: int) -> List[Dict]:
    """Get all cohorts (and the groups in each cohort) that the user is a part of along with their role in each group"""
    results = await execute_db_operation(
        f"""
        SELECT c.id, c.name, uc.role, o.id, o.name
        FROM {cohorts_table_name} c
        JOIN {user_cohorts_table_name} uc ON uc.cohort_id = c.id
        JOIN {organizations_table_name} o ON o.id = c.org_id
        WHERE uc.user_id = ?
        """,
        (user_id,),
        fetch_all=True,
    )

    # Convert results into nested dict structure
    return [
        {
            "id": cohort_id,
            "name": cohort_name,
            "org_id": org_id,
            "org_name": org_name,
            "role": role,
        }
        for cohort_id, cohort_name, role, org_id, org_name in results
    ]


async def get_user_active_in_last_n_days(user_id: int, n: int, cohort_id: int):
    activity_per_day = await execute_db_operation(
        f"""
    WITH chat_activity AS (
        SELECT DATE(datetime(created_at, '+5 hours', '+30 minutes')) as activity_date, COUNT(*) as count
        FROM {chat_history_table_name}
        WHERE user_id = ? 
        AND DATE(datetime(created_at, '+5 hours', '+30 minutes')) >= DATE(datetime('now', '+5 hours', '+30 minutes'), '-{n} days') 
        AND question_id IN (
            SELECT question_id 
            FROM {questions_table_name} 
            WHERE task_id IN (
                SELECT task_id 
                FROM {course_tasks_table_name} 
                WHERE course_id IN (
                    SELECT course_id 
                    FROM {course_cohorts_table_name} 
                    WHERE cohort_id = ?
                )
            )
        )
        GROUP BY activity_date
    ),
    task_activity AS (
        SELECT DATE(datetime(created_at, '+5 hours', '+30 minutes')) as activity_date, COUNT(*) as count
        FROM {task_completions_table_name}
        WHERE user_id = ? 
        AND DATE(datetime(created_at, '+5 hours', '+30 minutes')) >= DATE(datetime('now', '+5 hours', '+30 minutes'), '-{n} days')
        AND task_id IN (
            SELECT task_id 
            FROM {course_tasks_table_name} 
            WHERE course_id IN (
                SELECT course_id 
                FROM {course_cohorts_table_name} 
                WHERE cohort_id = ?
            )
        )
        GROUP BY activity_date
    )
    SELECT activity_date, count FROM chat_activity
    UNION
    SELECT activity_date, count FROM task_activity
    ORDER BY activity_date
    """,
        (user_id, cohort_id, user_id, cohort_id),
        fetch_all=True,
    )

    active_days = set()

    for date, count in activity_per_day:
        if count > 0:
            active_days.add(date)

    return list(active_days)


async def get_user_activity_for_year(user_id: int, year: int):
    # Get all chat messages for the user in the given year, grouped by day
    activity_per_day = await execute_db_operation(
        f"""
        SELECT 
            strftime('%j', datetime(timestamp, '+5 hours', '+30 minutes')) as day_of_year,
            COUNT(*) as message_count
        FROM {chat_history_table_name}
        WHERE user_id = ? 
        AND strftime('%Y', datetime(timestamp, '+5 hours', '+30 minutes')) = ?
        AND role = 'user'
        GROUP BY day_of_year
        ORDER BY day_of_year
        """,
        (user_id, str(year)),
        fetch_all=True,
    )

    # Convert to dictionary mapping day of year to message count
    activity_map = {int(day) - 1: count for day, count in activity_per_day}

    num_days = 366 if not year % 4 else 365

    data = [activity_map.get(index, 0) for index in range(num_days)]

    return data


def get_user_streak_from_usage_dates(user_usage_dates: List[str]) -> int:
    if not user_usage_dates:
        return []

    today = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
    current_streak = []

    user_usage_dates = sorted(
        list(
            set([get_date_from_str(date_str, "IST") for date_str in user_usage_dates])
        ),
        reverse=True,
    )

    for i, date in enumerate(user_usage_dates):
        if i == 0 and (today - date).days > 1:
            # the user has not used the app yesterday or today, so the streak is broken
            break
        if i == 0 or (user_usage_dates[i - 1] - date).days == 1:
            current_streak.append(date)
        else:
            break

    if not current_streak:
        return current_streak

    for index, date in enumerate(current_streak):
        current_streak[index] = datetime.strftime(date, "%Y-%m-%d")

    return current_streak


async def get_user_streak(user_id: int, cohort_id: int):
    user_usage_dates = await execute_db_operation(
        f"""
    SELECT MAX(datetime(created_at, '+5 hours', '+30 minutes')) as created_at
    FROM {chat_history_table_name}
    WHERE user_id = ? AND question_id IN (SELECT id FROM {questions_table_name} WHERE task_id IN (SELECT task_id FROM {course_tasks_table_name} WHERE course_id IN (SELECT course_id FROM {course_cohorts_table_name} WHERE cohort_id = ?)))
    GROUP BY DATE(datetime(created_at, '+5 hours', '+30 minutes'))
    
    UNION
    
    SELECT MAX(datetime(created_at, '+5 hours', '+30 minutes')) as created_at
    FROM {task_completions_table_name}
    WHERE user_id = ? AND task_id IN (
        SELECT task_id FROM {course_tasks_table_name} 
        WHERE course_id IN (SELECT course_id FROM {course_cohorts_table_name} WHERE cohort_id = ?)
    )
    GROUP BY DATE(datetime(created_at, '+5 hours', '+30 minutes'))
    
    ORDER BY created_at DESC
    """,
        (user_id, cohort_id, user_id, cohort_id),
        fetch_all=True,
    )

    return get_user_streak_from_usage_dates(
        [date_str for date_str, in user_usage_dates]
    )

async def create_candidate_profile(conn: sqlite3.Connection, user_id: int) -> NewCandidateProfileRead:
    """Creates a new candidate profile for a given user_id."""
    cursor = await conn.cursor()
    await cursor.execute(
        """INSERT INTO NEW_candidate_profiles (NEW_user_id) VALUES (?)""",
        (user_id,)
    )
    # No commit here, as it's expected to be part of a larger transaction
    return NewCandidateProfileRead(
        new_user_id=user_id,
        new_status="ACTIVE",
        new_updated_at=datetime.now() # This will be updated by the DB, but for consistency
    )

async def update_candidate_profile(conn: sqlite3.Connection, user_id: int, profile_data: NewCandidateProfileUpdate) -> Optional[NewCandidateProfileRead]:
    """Updates an existing candidate profile."""
    cursor = await conn.cursor()
    update_fields = []
    params = []

    if profile_data.new_phone_number is not None:
        update_fields.append("NEW_phone_number = ?")
        params.append(profile_data.new_phone_number)
    if profile_data.new_location is not None:
        update_fields.append("NEW_location = ?")
        params.append(profile_data.new_location)
    if profile_data.new_bio is not None:
        update_fields.append("NEW_bio = ?")
        params.append(profile_data.new_bio)
    if profile_data.new_resume_url is not None:
        update_fields.append("NEW_resume_url = ?")
        params.append(profile_data.new_resume_url)
    if profile_data.new_linkedin_profile is not None:
        update_fields.append("NEW_linkedin_profile = ?")
        params.append(profile_data.new_linkedin_profile)
    if profile_data.new_portfolio_url is not None:
        update_fields.append("NEW_portfolio_url = ?")
        params.append(profile_data.new_portfolio_url)

    if not update_fields:
        return await get_candidate_profile(user_id) # No fields to update

    params.append(user_id)
    update_query = f"""UPDATE NEW_candidate_profiles SET {", ".join(update_fields)}, NEW_updated_at = CURRENT_TIMESTAMP WHERE NEW_user_id = ?"""
    
    await cursor.execute(update_query, tuple(params))
    # No commit here, as it's expected to be part of a larger transaction
    
    if cursor.rowcount > 0:
        # Re-fetch the updated profile including all fields, as some might be defaults or calculated by DB
        return await get_candidate_profile(user_id)
    return None

async def get_candidate_profile(user_id: int) -> Optional[NewCandidateProfileRead]:
    """Retrieves a candidate profile by user ID."""
    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """SELECT NEW_user_id, NEW_phone_number, NEW_location, NEW_bio, NEW_resume_url, NEW_linkedin_profile, NEW_portfolio_url, NEW_status, NEW_cooldown_until, NEW_updated_at
            FROM NEW_candidate_profiles WHERE NEW_user_id = ?""",
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return NewCandidateProfileRead(
                new_user_id=row[0],
                new_phone_number=row[1],
                new_location=row[2],
                new_bio=row[3],
                new_resume_url=row[4],
                new_linkedin_profile=row[5],
                new_portfolio_url=row[6],
                new_status=row[7],
                new_cooldown_until=datetime.fromisoformat(row[8]) if isinstance(row[8], str) else row[8],
                new_updated_at=datetime.fromisoformat(row[9]) if isinstance(row[9], str) else row[9]
            )
        return None
