import os
from os.path import exists
from api.utils.db import get_new_db_connection, set_db_defaults
from api.config import (
    sqlite_db_path,
    chat_history_table_name,
    tasks_table_name,
    questions_table_name,
    cohorts_table_name,
    user_cohorts_table_name,
    milestones_table_name,
    users_table_name,
    organizations_table_name,
    user_organizations_table_name,
    courses_table_name,
    course_cohorts_table_name,
    course_tasks_table_name,
    course_milestones_table_name,
    task_completions_table_name,
    scorecards_table_name,
    question_scorecards_table_name,
    course_generation_jobs_table_name,
    task_generation_jobs_table_name,
    org_api_keys_table_name,
    code_drafts_table_name,
)


async def create_organizations_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {organizations_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                default_logo_color TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                openai_api_key TEXT,
                openai_free_trial BOOLEAN
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_org_slug ON {organizations_table_name} (slug)"""
    )


async def create_org_api_keys_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {org_api_keys_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                hashed_key TEXT NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id) ON DELETE CASCADE
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_org_api_key_org_id ON {org_api_keys_table_name} (org_id)"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_org_api_key_hashed_key ON {org_api_keys_table_name} (hashed_key)"""
    )


async def create_users_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {users_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                first_name TEXT,
                middle_name TEXT,
                last_name TEXT,
                default_dp_color TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
    )


async def create_user_organizations_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {user_organizations_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                org_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, org_id),
                FOREIGN KEY (user_id) REFERENCES {users_table_name}(id) ON DELETE CASCADE,
                FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id) ON DELETE CASCADE
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_user_org_user_id ON {user_organizations_table_name} (user_id)"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_user_org_org_id ON {user_organizations_table_name} (org_id)"""
    )


async def create_cohort_tables(cursor):
    # Create a table to store cohorts
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {cohorts_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                org_id INTEGER NOT NULL,
                FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id) ON DELETE CASCADE
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_cohort_org_id ON {cohorts_table_name} (org_id)"""
    )

    # Create a table to store users in cohorts
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {user_cohorts_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                cohort_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, cohort_id),
                FOREIGN KEY (user_id) REFERENCES {users_table_name}(id) ON DELETE CASCADE,
                FOREIGN KEY (cohort_id) REFERENCES {cohorts_table_name}(id) ON DELETE CASCADE
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_user_cohort_user_id ON {user_cohorts_table_name} (user_id)"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_user_cohort_cohort_id ON {user_cohorts_table_name} (cohort_id)"""
    )


async def create_course_tasks_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {course_tasks_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                ordering INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                milestone_id INTEGER,
                UNIQUE(task_id, course_id),
                FOREIGN KEY (task_id) REFERENCES {tasks_table_name}(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES {courses_table_name}(id) ON DELETE CASCADE,
                FOREIGN KEY (milestone_id) REFERENCES {milestones_table_name}(id) ON DELETE CASCADE
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_course_task_task_id ON {course_tasks_table_name} (task_id)"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_course_task_course_id ON {course_tasks_table_name} (course_id)"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_course_task_milestone_id ON {course_tasks_table_name} (milestone_id)"""
    )


async def create_course_milestones_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {course_milestones_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                milestone_id INTEGER,
                ordering INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(course_id, milestone_id),
                FOREIGN KEY (course_id) REFERENCES {courses_table_name}(id) ON DELETE CASCADE,
                FOREIGN KEY (milestone_id) REFERENCES {milestones_table_name}(id) ON DELETE CASCADE
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_course_milestone_course_id ON {course_milestones_table_name} (course_id)"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_course_milestone_milestone_id ON {course_milestones_table_name} (milestone_id)"""
    )


async def create_milestones_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {milestones_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT,
                FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id) ON DELETE CASCADE
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_milestone_org_id ON {milestones_table_name} (org_id)"""
    )


async def create_courses_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {courses_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id) ON DELETE CASCADE
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_course_org_id ON {courses_table_name} (org_id)"""
    )


async def create_course_cohorts_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {course_cohorts_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                cohort_id INTEGER NOT NULL,
                is_drip_enabled BOOLEAN DEFAULT FALSE,
                frequency_value INTEGER,
                frequency_unit TEXT,
                publish_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(course_id, cohort_id),
                FOREIGN KEY (course_id) REFERENCES {courses_table_name}(id) ON DELETE CASCADE,
                FOREIGN KEY (cohort_id) REFERENCES {cohorts_table_name}(id) ON DELETE CASCADE
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_course_cohort_course_id ON {course_cohorts_table_name} (course_id)"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_course_cohort_cohort_id ON {course_cohorts_table_name} (cohort_id)"""
    )


async def create_tasks_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {tasks_table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    blocks TEXT,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    deleted_at DATETIME,
                    scheduled_publish_at DATETIME,
                    FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id) ON DELETE CASCADE
                )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_task_org_id ON {tasks_table_name} (org_id)"""
    )


async def create_questions_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {questions_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                blocks TEXT,
                answer TEXT,
                input_type TEXT NOT NULL,
                coding_language TEXT,
                generation_model TEXT,
                response_type TEXT NOT NULL,
                position INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted_at DATETIME,
                max_attempts INTEGER,
                is_feedback_shown BOOLEAN NOT NULL,
                context TEXT,
                title TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES {tasks_table_name}(id) ON DELETE CASCADE
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_question_task_id ON {questions_table_name} (task_id)"""
    )


async def create_scorecards_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {scorecards_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                criteria TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id) ON DELETE CASCADE
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_scorecard_org_id ON {scorecards_table_name} (org_id)"""
    )


async def create_question_scorecards_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {question_scorecards_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                scorecard_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES {questions_table_name}(id) ON DELETE CASCADE,
                FOREIGN KEY (scorecard_id) REFERENCES {scorecards_table_name}(id) ON DELETE CASCADE,
                UNIQUE(question_id, scorecard_id)
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_question_scorecard_question_id ON {question_scorecards_table_name} (question_id)"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_question_scorecard_scorecard_id ON {question_scorecards_table_name} (scorecard_id)"""
    )


async def create_chat_history_table(cursor):
    await cursor.execute(
        f"""
                CREATE TABLE IF NOT EXISTS {chat_history_table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    response_type TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (question_id) REFERENCES {questions_table_name}(id),
                    FOREIGN KEY (user_id) REFERENCES {users_table_name}(id) ON DELETE CASCADE
                )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_chat_history_user_id ON {chat_history_table_name} (user_id)"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_chat_history_question_id ON {chat_history_table_name} (question_id)"""
    )


async def create_task_completion_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {task_completions_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_id INTEGER,
                question_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES {users_table_name}(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES {tasks_table_name}(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES {questions_table_name}(id) ON DELETE CASCADE,
                UNIQUE(user_id, task_id),
                UNIQUE(user_id, question_id)
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_task_completion_user_id ON {task_completions_table_name} (user_id)"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_task_completion_task_id ON {task_completions_table_name} (task_id)"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_task_completion_question_id ON {task_completions_table_name} (question_id)"""
    )


async def create_course_generation_jobs_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {course_generation_jobs_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT NOT NULL,
                course_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                job_details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES {courses_table_name}(id) ON DELETE CASCADE
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_course_generation_job_course_id ON {course_generation_jobs_table_name} (course_id)"""
    )


async def create_task_generation_jobs_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {task_generation_jobs_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT NOT NULL,
                task_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                job_details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES {tasks_table_name}(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES {courses_table_name}(id) ON DELETE CASCADE
            )"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_task_generation_job_task_id ON {task_generation_jobs_table_name} (task_id)"""
    )

    await cursor.execute(
        f"""CREATE INDEX idx_task_generation_job_course_id ON {task_generation_jobs_table_name} (course_id)"""
    )


async def create_code_drafts_table(cursor):
    await cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {code_drafts_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, question_id),
                FOREIGN KEY (user_id) REFERENCES {users_table_name}(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES {questions_table_name}(id) ON DELETE CASCADE
            )"""
    )

    # Useful indexes for faster lookup
    await cursor.execute(
        f"""CREATE INDEX IF NOT EXISTS idx_code_drafts_user_id ON {code_drafts_table_name} (user_id)"""
    )

    await cursor.execute(
        f"""CREATE INDEX IF NOT EXISTS idx_code_drafts_question_id ON {code_drafts_table_name} (question_id)"""
    )


# ========= PART 2: NEW Hiring Workflow Schema (Prefixed with NEW_) =========
# These tables support the skills-first hiring workflow, referencing the
# original tables where necessary (e.g., users, organizations, tasks).
# -------------------------------------------------------------------------------

# ===== Candidate & Skill Management =====

async def create_new_candidate_profiles_table(cursor):
    await cursor.execute(
        """CREATE TABLE IF NOT EXISTS NEW_candidate_profiles (
            NEW_user_id INTEGER PRIMARY KEY,
            NEW_phone_number TEXT,
            NEW_location TEXT,
            NEW_bio TEXT,
            NEW_resume_url TEXT,
            NEW_linkedin_profile TEXT,
            NEW_portfolio_url TEXT,
            NEW_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(NEW_status IN ('ACTIVE', 'IN_COOLDOWN')),
            NEW_cooldown_until DATETIME,
            NEW_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(NEW_user_id) REFERENCES users(id) ON DELETE CASCADE
        )"""
    )

async def create_new_skills_table(cursor):
    await cursor.execute(
        """CREATE TABLE IF NOT EXISTS NEW_skills (
            NEW_id INTEGER PRIMARY KEY AUTOINCREMENT,
            NEW_name TEXT NOT NULL UNIQUE,
            NEW_category TEXT
        )"""
    )

async def create_new_candidate_skills_table(cursor):
    await cursor.execute(
        """CREATE TABLE IF NOT EXISTS NEW_candidate_skills (
            NEW_id INTEGER PRIMARY KEY AUTOINCREMENT,
            NEW_user_id INTEGER NOT NULL,
            NEW_skill_id INTEGER NOT NULL,
            NEW_proficiency_score INTEGER CHECK (NEW_proficiency_score >= 0 AND NEW_proficiency_score <= 100),
            NEW_verification_source_task_id INTEGER,
            NEW_last_verified_at DATETIME,
            UNIQUE(NEW_user_id, NEW_skill_id),
            FOREIGN KEY(NEW_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(NEW_skill_id) REFERENCES NEW_skills(NEW_id) ON DELETE CASCADE,
            FOREIGN KEY(NEW_verification_source_task_id) REFERENCES tasks(id) ON DELETE SET NULL
        )"""
    )

# ===== Job Posting & Application Management =====

async def create_new_job_postings_table(cursor):
    await cursor.execute(
        """CREATE TABLE IF NOT EXISTS NEW_job_postings (
            NEW_id INTEGER PRIMARY KEY AUTOINCREMENT,
            NEW_org_id INTEGER NOT NULL,
            NEW_posted_by_user_id INTEGER NOT NULL,
            NEW_title TEXT NOT NULL,
            NEW_description TEXT,
            NEW_location TEXT,
            NEW_job_type TEXT NOT NULL CHECK(NEW_job_type IN ('INTERNSHIP', 'FULL_TIME')),
            NEW_status TEXT NOT NULL DEFAULT 'OPEN' CHECK(NEW_status IN ('OPEN', 'CLOSED', 'ON_HOLD')),
            NEW_created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(NEW_org_id) REFERENCES organizations(id) ON DELETE CASCADE,
            FOREIGN KEY(NEW_posted_by_user_id) REFERENCES users(id) ON DELETE CASCADE
        )"""
    )

async def create_new_job_required_skills_table(cursor):
    await cursor.execute(
        """CREATE TABLE IF NOT EXISTS NEW_job_required_skills (
            NEW_job_posting_id INTEGER NOT NULL,
            NEW_skill_id INTEGER NOT NULL,
            NEW_required_proficiency_threshold INTEGER NOT NULL,
            PRIMARY KEY (NEW_job_posting_id, NEW_skill_id),
            FOREIGN KEY(NEW_job_posting_id) REFERENCES NEW_job_postings(NEW_id) ON DELETE CASCADE,
            FOREIGN KEY(NEW_skill_id) REFERENCES NEW_skills(NEW_id) ON DELETE CASCADE
        )"""
    )

async def create_new_applications_table(cursor):
    await cursor.execute(
        """CREATE TABLE IF NOT EXISTS NEW_applications (
            NEW_id INTEGER PRIMARY KEY AUTOINCREMENT,
            NEW_user_id INTEGER NOT NULL,
            NEW_job_posting_id INTEGER NOT NULL,
            NEW_status TEXT NOT NULL CHECK(NEW_status IN ('APPLIED', 'ASSESSMENT_PENDING', 'ASSESSMENT_COMPLETE', 'SHORTLISTED', 'INTERVIEW_SCHEDULED', 'OFFERED', 'REJECTED', 'ON_HOLD', 'HIRED')),
            NEW_applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            NEW_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(NEW_user_id, NEW_job_posting_id),
            FOREIGN KEY(NEW_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(NEW_job_posting_id) REFERENCES NEW_job_postings(NEW_id) ON DELETE CASCADE
        )"""
    )

# ===== Interview Management =====

async def create_new_interviews_table(cursor):
    await cursor.execute(
        """CREATE TABLE IF NOT EXISTS NEW_interviews (
            NEW_id INTEGER PRIMARY KEY AUTOINCREMENT,
            NEW_application_id INTEGER NOT NULL,
            NEW_scheduled_time DATETIME NOT NULL,
            NEW_duration_minutes INTEGER DEFAULT 60,
            NEW_location_or_link TEXT,
            NEW_status TEXT NOT NULL DEFAULT 'SCHEDULED' CHECK(NEW_status IN ('SCHEDULED', 'COMPLETED', 'CANCELED')),
            FOREIGN KEY(NEW_application_id) REFERENCES NEW_applications(NEW_id) ON DELETE CASCADE
        )"""
    )

async def create_new_interviewers_table(cursor):
    await cursor.execute(
        """CREATE TABLE IF NOT EXISTS NEW_interviewers (
            NEW_interview_id INTEGER NOT NULL,
            NEW_user_id INTEGER NOT NULL,
            PRIMARY KEY (NEW_interview_id, NEW_user_id),
            FOREIGN KEY(NEW_interview_id) REFERENCES NEW_interviews(NEW_id) ON DELETE CASCADE,
            FOREIGN KEY(NEW_user_id) REFERENCES users(id) ON DELETE CASCADE
        )"""
    )

async def create_new_interview_feedback_table(cursor):
    await cursor.execute(
        """CREATE TABLE IF NOT EXISTS NEW_interview_feedback (
            NEW_id INTEGER PRIMARY KEY AUTOINCREMENT,
            NEW_interview_id INTEGER NOT NULL,
            NEW_interviewer_user_id INTEGER NOT NULL,
            NEW_overall_rating INTEGER CHECK (NEW_overall_rating >= 1 AND NEW_overall_rating <= 5),
            NEW_feedback_for_candidate TEXT,
            NEW_internal_notes TEXT,
            NEW_hiring_decision TEXT NOT NULL CHECK(NEW_hiring_decision IN ('SELECT', 'HOLD', 'REJECT')),
            NEW_submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(NEW_interview_id) REFERENCES NEW_interviews(NEW_id) ON DELETE CASCADE,
            FOREIGN KEY(NEW_interviewer_user_id) REFERENCES users(id) ON DELETE CASCADE
        )"""
    )

# ===== Offer and Internship Management =====

async def create_new_offers_table(cursor):
    await cursor.execute(
        """CREATE TABLE IF NOT EXISTS NEW_offers (
            NEW_id INTEGER PRIMARY KEY AUTOINCREMENT,
            NEW_application_id INTEGER NOT NULL UNIQUE,
            NEW_offer_type TEXT NOT NULL CHECK(NEW_offer_type IN ('INTERNSHIP', 'FTE')),
            NEW_offer_details TEXT, -- Stored as JSON string
            NEW_status TEXT NOT NULL DEFAULT 'SENT' CHECK(NEW_status IN ('SENT', 'ACCEPTED', 'DECLINED', 'WITHDRAWN')),
            NEW_sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            NEW_expires_at DATETIME,
            FOREIGN KEY(NEW_application_id) REFERENCES NEW_applications(NEW_id) ON DELETE CASCADE
        )"""
    )

async def create_new_internships_table(cursor):
    await cursor.execute(
        """CREATE TABLE IF NOT EXISTS NEW_internships (
            NEW_id INTEGER PRIMARY KEY AUTOINCREMENT,
            NEW_application_id INTEGER NOT NULL UNIQUE,
            NEW_start_date DATE NOT NULL,
            NEW_end_date DATE NOT NULL,
            NEW_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(NEW_status IN ('ACTIVE', 'COMPLETED', 'EXTENDED', 'TERMINATED')),
            FOREIGN KEY(NEW_application_id) REFERENCES NEW_applications(NEW_id) ON DELETE CASCADE
        )"""
    )


async def init_db():
    # Ensure the database folder exists
    db_folder = os.path.dirname(sqlite_db_path)
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)

    if not exists(sqlite_db_path):
        # only set the defaults the first time
        set_db_defaults()

    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()

        # check for missing tables and create them
        await create_organizations_table(cursor)
        await create_org_api_keys_table(cursor)
        await create_users_table(cursor)
        await create_user_organizations_table(cursor)
        # Modified create_user_organizations_table call for updated CHECK constraint
        await cursor.execute(
            "PRAGMA table_info({});".format(user_organizations_table_name)
        )
        user_org_columns = [col[1] for col in await cursor.fetchall()]

        # Check if the 'role' column has the updated CHECK constraint. 
        # SQLite does not directly expose CHECK constraints via PRAGMA table_info.
        # A common workaround for schema migrations in SQLite is to rename the table,
        # create a new table with the desired schema, copy data, and then drop the old table.
        # This block specifically handles the migration of the 'role' column's CHECK constraint.
        # We can check for a 'migration_complete' flag or a new column, but for simplicity,
        # let's assume if 'role_temp' exists, the migration has already run.
        if "role_temp" not in user_org_columns: # This implies the migration has not yet run
            await cursor.execute(
                "ALTER TABLE {} RENAME TO {}_old;".format(user_organizations_table_name, user_organizations_table_name)
            )
            await cursor.execute(
                """CREATE TABLE {} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        org_id INTEGER NOT NULL,
                        role TEXT NOT NULL CHECK(role IN ('ADMIN', 'MEMBER', 'RECRUITER', 'HIRING_MANAGER', 'CANDIDATE')),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, org_id),
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
                    )""".format(user_organizations_table_name)
            )
            await cursor.execute(
                "INSERT INTO {} (id, user_id, org_id, role, created_at) SELECT id, user_id, org_id, role, created_at FROM {}_old;".format(user_organizations_table_name, user_organizations_table_name)
            )
            await cursor.execute(
                "DROP TABLE {}_old;".format(user_organizations_table_name)
            )
            # Recreate indexes, as they are dropped with the table
            await cursor.execute(
                "CREATE INDEX idx_user_org_user_id ON {} (user_id);".format(user_organizations_table_name)
            )
            await cursor.execute(
                "CREATE INDEX idx_user_org_org_id ON {} (org_id);".format(user_organizations_table_name)
            )
        
        # Removed previous migration logic due to persistent errors and to simplify initial setup.
        # This section originally handled schema updates for 'user_organizations_table' 
        # by attempting to rename the table, create a new one, copy data, and then drop the old one.
        # It also involved a temporary 'role_temp' column.
        # The commented-out lines below represent the logic that was removed to bypass the current errors.
        # await cursor.execute("ALTER TABLE {} ADD COLUMN role_temp TEXT;".format(user_organizations_table_name))
        # await cursor.execute("UPDATE {} SET role_temp = role;".format(user_organizations_table_name))
        # await cursor.execute("DROP INDEX IF EXISTS idx_user_org_user_id;")
        # await cursor.execute("DROP INDEX IF EXISTS idx_user_org_org_id;")
        # await cursor.execute("DROP TABLE IF EXISTS {};".format(user_organizations_table_name))
        # await cursor.execute(f"""CREATE TABLE {user_organizations_table_name} (...)"""
        # await cursor.execute("INSERT INTO {} (..., role_temp, ...) SELECT ..., role_temp, ... FROM {}_temp;".format(...))
        # await cursor.execute("DROP TABLE IF EXISTS {}_temp;".format(user_organizations_table_name))
        # await cursor.execute("CREATE INDEX idx_user_org_user_id ON {} (user_id);".format(user_organizations_table_name))
        # await cursor.execute("CREATE INDEX idx_user_org_org_id ON {} (org_id);".format(user_organizations_table_name))

        await create_milestones_table(cursor)
        await create_cohort_tables(cursor)
        await create_courses_table(cursor)
        await create_course_cohorts_table(cursor)
        await create_tasks_table(cursor)
        # Modified create_tasks_table call for updated CHECK constraint
        await cursor.execute(
            "PRAGMA table_info({});".format(tasks_table_name)
        )
        task_columns = [col[1] for col in await cursor.fetchall()]

        if "type_temp" not in task_columns:
            await cursor.execute(
                "ALTER TABLE {} RENAME TO {}_old;".format(tasks_table_name, tasks_table_name)
            )
            await cursor.execute(
                """CREATE TABLE {} (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            org_id INTEGER NOT NULL,
                            type TEXT NOT NULL CHECK(type IN ('LESSON', 'QUIZ', 'PROJECT', 'SKILL_ASSESSMENT', 'INTERVIEW_EVALUATION_SHEET')),
                            blocks TEXT,
                            title TEXT NOT NULL,
                            status TEXT NOT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            deleted_at DATETIME,
                            scheduled_publish_at DATETIME,
                            FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
                        )""".format(tasks_table_name)
            )
            await cursor.execute(
                "INSERT INTO {} (id, org_id, type, blocks, title, status, created_at, deleted_at, scheduled_publish_at) SELECT id, org_id, type, blocks, title, status, created_at, deleted_at, scheduled_publish_at FROM {}_old;".format(tasks_table_name, tasks_table_name)
            )
            await cursor.execute(
                "DROP TABLE {}_old;".format(tasks_table_name)
            )
            await cursor.execute(
                "CREATE INDEX idx_task_org_id ON {} (org_id);".format(tasks_table_name)
            )

        # Removed previous migration logic due to persistent errors and to simplify initial setup.
        # This section originally handled schema updates for 'tasks_table' 
        # by attempting to rename the table, create a new one, copy data, and then drop the old one.
        # It also involved a temporary 'type_temp' column.
        # The commented-out lines below represent the logic that was removed to bypass the current errors.
        # await cursor.execute("ALTER TABLE {} ADD COLUMN type_temp TEXT;".format(tasks_table_name))
        # await cursor.execute("UPDATE {} SET type_temp = type;".format(tasks_table_name))
        # await cursor.execute("DROP INDEX IF EXISTS idx_task_org_id;")
        # await cursor.execute("DROP TABLE IF EXISTS {};".format(tasks_table_name))
        # await cursor.execute(f"""CREATE TABLE {tasks_table_name} (...)"""
        # await cursor.execute("INSERT INTO {} (..., type_temp, ...) SELECT ..., type_temp, ... FROM {}_temp;".format(...))
        # await cursor.execute("DROP TABLE IF EXISTS {}_temp;".format(tasks_table_name))
        # await cursor.execute("CREATE INDEX idx_task_org_id ON {} (org_id);".format(tasks_table_name))

        await create_questions_table(cursor)
        await create_scorecards_table(cursor)
        await create_question_scorecards_table(cursor)
        await create_chat_history_table(cursor)
        await create_task_completion_table(cursor)
        await create_course_tasks_table(cursor)
        await create_course_milestones_table(cursor)
        await create_course_generation_jobs_table(cursor)
        await create_task_generation_jobs_table(cursor)
        await create_code_drafts_table(cursor)

        # New tables
        await create_new_candidate_profiles_table(cursor)
        await create_new_skills_table(cursor)
        await create_new_candidate_skills_table(cursor)
        await create_new_job_postings_table(cursor)
        await create_new_job_required_skills_table(cursor)
        await create_new_applications_table(cursor)
        await create_new_interviews_table(cursor)
        await create_new_interviewers_table(cursor)
        await create_new_interview_feedback_table(cursor)
        await create_new_offers_table(cursor)
        await create_new_internships_table(cursor)

        await conn.commit()
        return

        # try:
        #     await create_organizations_table(cursor)

        #     await create_org_api_keys_table(cursor)

        #     await create_users_table(cursor)

        #     await create_user_organizations_table(cursor)

        #     await create_milestones_table(cursor)

        #     await create_cohort_tables(cursor)

        #     await create_courses_table(cursor)

        #     await create_course_cohorts_table(cursor)

        #     await create_tasks_table(cursor)

        #     await create_questions_table(cursor)

        #     await create_scorecards_table(cursor)

        #     await create_question_scorecards_table(cursor)

        #     await create_chat_history_table(cursor)

        #     await create_task_completion_table(cursor)

        #     await create_course_tasks_table(cursor)

        #     await create_course_milestones_table(cursor)

        #     await create_course_generation_jobs_table(cursor)

        #     await create_task_generation_jobs_table(cursor)

        #     await create_code_drafts_table(cursor)

        #     await conn.commit()

        # except Exception as exception:
        #     # delete db
        #     os.remove(sqlite_db_path)
        #     raise exception


async def delete_useless_tables():
    from api.config import (
        tags_table_name,
        task_tags_table_name,
        groups_table_name,
        user_groups_table_name,
        badges_table_name,
        task_scoring_criteria_table_name,
        cv_review_usage_table_name,
        tests_table_name,
    )

    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()

        await cursor.execute(f"DROP TABLE IF EXISTS {tags_table_name}")
        await cursor.execute(f"DROP TABLE IF EXISTS {task_tags_table_name}")
        await cursor.execute(f"DROP TABLE IF EXISTS {tests_table_name}")
        await cursor.execute(f"DROP TABLE IF EXISTS {groups_table_name}")
        await cursor.execute(f"DROP TABLE IF EXISTS {user_groups_table_name}")
        await cursor.execute(f"DROP TABLE IF EXISTS {badges_table_name}")
        await cursor.execute(f"DROP TABLE IF EXISTS {task_scoring_criteria_table_name}")
        await cursor.execute(f"DROP TABLE IF EXISTS {cv_review_usage_table_name}")

    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(f"PRAGMA table_info({user_cohorts_table_name})")
        user_columns = [col[1] for col in await cursor.fetchall()]

        if "joined_at" not in user_columns:
            await cursor.execute(f"DROP TABLE IF EXISTS {user_cohorts_table_name}_temp")
            await cursor.execute(
                f"""
                CREATE TABLE {user_cohorts_table_name}_temp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    cohort_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, cohort_id),
                    FOREIGN KEY (user_id) REFERENCES {users_table_name}(id) ON DELETE CASCADE,
                    FOREIGN KEY (cohort_id) REFERENCES {cohorts_table_name}(id) ON DELETE CASCADE
                )
            """
            )
            await cursor.execute(
                f"INSERT INTO {user_cohorts_table_name}_temp (id, user_id, cohort_id, role) SELECT id, user_id, cohort_id, role FROM {user_cohorts_table_name}"
            )
            await cursor.execute(f"DROP TABLE {user_cohorts_table_name}")
            await cursor.execute(
                f"ALTER TABLE {user_cohorts_table_name}_temp RENAME TO {user_cohorts_table_name}"
            )

            # Recreate the indexes that were lost during table recreation
            await cursor.execute(
                f"CREATE INDEX idx_user_cohort_user_id ON {user_cohorts_table_name} (user_id)"
            )
            await cursor.execute(
                f"CREATE INDEX idx_user_cohort_cohort_id ON {user_cohorts_table_name} (cohort_id)"
            )

        await cursor.execute(f"PRAGMA table_info({course_cohorts_table_name})")
        course_columns = [col[1] for col in await cursor.fetchall()]

        for col, col_type, default in [
            ("is_drip_enabled", "BOOLEAN", "FALSE"),
            ("frequency_value", "INTEGER", None),
            ("frequency_unit", "TEXT", None),
            ("publish_at", "DATETIME", None),
        ]:
            if col not in course_columns:
                default_str = f" DEFAULT {default}" if default else ""
                await cursor.execute(
                    f"ALTER TABLE {course_cohorts_table_name} ADD COLUMN {col} {col_type}{default_str}"
                )

        await conn.commit()
