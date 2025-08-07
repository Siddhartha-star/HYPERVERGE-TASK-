import pytest
from unittest.mock import AsyncMock, patch
from api.services.matching_service import find_matching_candidates
from api.db.job_posting_db import create_job_posting
from api.db.skill_db import create_skill, create_or_update_candidate_skill
from api.db.user import insert_or_return_user, create_candidate_profile
from api.models import NewSkill, NewJobPostingCreate
from api.utils.db import get_new_db_connection

@pytest.fixture(autouse=True)
async def setup_db_for_matching_service_tests():
    # Ensure the database is initialized before each test
    # This fixture should run before any test that uses the database
    from api.db import init_db
    await init_db.init_db()

@pytest.fixture
async def prepopulated_db_for_matching_service():
    async with get_new_db_connection() as conn:
        # Create skills
        skill1 = await create_skill(NewSkill(new_name="Python", new_category="Programming"))
        skill2 = await create_skill(NewSkill(new_name="SQL", new_category="Databases"))
        skill3 = await create_skill(NewSkill(new_name="Machine Learning", new_category="AI"))
        skill4 = await create_skill(NewSkill(new_name="Communication", new_category="Soft Skills"))

        # Create a job posting with required skills
        job_data = NewJobPostingCreate(
            new_org_id=1,
            new_title="Senior ML Engineer",
            new_description="Requires strong Python, ML, and good communication.",
            new_location="Remote",
            new_job_type="FULL_TIME",
            required_skills=[
                {"skill_id": skill1.new_id, "threshold": 80},
                {"skill_id": skill3.new_id, "threshold": 90},
                {"skill_id": skill4.new_id, "threshold": 70},
            ]
        )
        posted_by_user_data, _ = await insert_or_return_user(conn.cursor(), "jobposter_match@example.com", "Job", "Poster")
        await conn.commit()
        job_posting = await create_job_posting(job_data, posted_by_user_data["id"])

        # Create candidates and their skills
        # Candidate 1: Full match
        candidate1_data, _ = await insert_or_return_user(conn.cursor(), "match1@example.com", "Match", "One")
        await conn.commit()
        await create_candidate_profile(conn, candidate1_data["id"])
        await create_or_update_candidate_skill(candidate1_data["id"], skill1.new_id, 85) # Python
        await create_or_update_candidate_skill(candidate1_data["id"], skill3.new_id, 92) # ML
        await create_or_update_candidate_skill(candidate1_data["id"], skill4.new_id, 75) # Communication
        await conn.commit()

        # Candidate 2: Partial match (missing one required skill - Communication)
        candidate2_data, _ = await insert_or_return_user(conn.cursor(), "partial_match2@example.com", "Partial", "Two")
        await conn.commit()
        await create_candidate_profile(conn, candidate2_data["id"])
        await create_or_update_candidate_skill(candidate2_data["id"], skill1.new_id, 90) # Python
        await create_or_update_candidate_skill(candidate2_data["id"], skill3.new_id, 95) # ML
        await create_or_update_candidate_skill(candidate2_data["id"], skill2.new_id, 80) # SQL (not required for this job)
        await conn.commit()

        # Candidate 3: No match (below threshold for a required skill - Python)
        candidate3_data, _ = await insert_or_return_user(conn.cursor(), "no_match3@example.com", "No", "Three")
        await conn.commit()
        await create_candidate_profile(conn, candidate3_data["id"])
        await create_or_update_candidate_skill(candidate3_data["id"], skill1.new_id, 70) # Python (below 80)
        await create_or_update_candidate_skill(candidate3_data["id"], skill3.new_id, 90) # ML
        await create_or_update_candidate_skill(candidate3_data["id"], skill4.new_id, 80) # Communication
        await conn.commit()

        yield job_posting.new_id, candidate1_data["id"], candidate2_data["id"], candidate3_data["id"]

@pytest.mark.asyncio
async def test_find_matching_candidates(prepopulated_db_for_matching_service):
    job_id, candidate1_id, candidate2_id, candidate3_id = await prepopulated_db_for_matching_service

    async with get_new_db_connection() as conn:
        matches = await find_matching_candidates(conn, job_id)
    
    assert len(matches) == 1
    assert matches[0]["user_id"] == candidate1_id
    assert matches[0]["first_name"] == "Match"
    assert matches[0]["match_score"] == (85 + 92 + 75) # Sum of proficiency scores

@pytest.mark.asyncio
async def test_find_matching_candidates_no_required_skills_for_job(setup_db_for_matching_service_tests):
    async with get_new_db_connection() as conn:
        # Create a job posting with no required skills
        job_data = NewJobPostingCreate(
            new_org_id=1,
            new_title="General Role",
            new_description="No specific skills required.",
            new_location="Anywhere",
            new_job_type="FULL_TIME",
            required_skills=[]
        )
        posted_by_user_data, _ = await insert_or_return_user(conn.cursor(), "generalposter@example.com", "General", "Poster")
        await conn.commit()
        job_posting = await create_job_posting(job_data, posted_by_user_data["id"])

        matches = await find_matching_candidates(conn, job_posting.new_id)
        assert len(matches) == 0 # No required skills, so no matches based on skill criteria

@pytest.mark.asyncio
async def test_find_matching_candidates_no_candidates(setup_db_for_matching_service_tests):
    async with get_new_db_connection() as conn:
        # Create a job posting with required skills
        skill = await create_skill(NewSkill(new_name="Testing", new_category="QA"))
        await conn.commit()
        job_data = NewJobPostingCreate(
            new_org_id=1,
            new_title="QA Engineer",
            new_description="Requires testing skills.",
            new_location="On-site",
            new_job_type="FULL_TIME",
            required_skills=[
                {"skill_id": skill.new_id, "threshold": 70},
            ]
        )
        posted_by_user_data, _ = await insert_or_return_user(conn.cursor(), "qaposter@example.com", "QA", "Poster")
        await conn.commit()
        job_posting = await create_job_posting(job_data, posted_by_user_data["id"])

        matches = await find_matching_candidates(conn, job_posting.new_id)
        assert len(matches) == 0 # No candidates exist with matching skills