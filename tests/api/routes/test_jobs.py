import pytest
from httpx import AsyncClient
from main import app
from api.db import init_db
from api.db.user import insert_or_return_user, create_candidate_profile
from api.db.org import create_organization, add_user_to_organization
from api.db.job_posting_db import create_job_posting
from api.db.skill_db import create_skill, create_or_update_candidate_skill
from api.models import CreateOrganizationRequest, NewJobPostingCreate, NewSkill
from api.utils.auth import get_current_user_id
from api.utils.db import get_new_db_connection

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db.init_db() # Ensure the database is initialized before each test

@pytest.fixture
async def recruiter_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with get_new_db_connection() as conn:
            cursor = await conn.cursor()
            user_data, _ = await insert_or_return_user(cursor, "recruiter@example.com", "Test", "Recruiter")
            await conn.commit()
            user_id = user_data["id"]

            org_data = CreateOrganizationRequest(name="Recruiter Org", slug="recruiter-org", user_id=user_id)
            new_org = await create_organization(cursor, org_data)
            await add_user_to_organization(cursor, user_id, new_org["id"], "RECRUITER")
            await conn.commit()
        
        app.dependency_overrides[get_current_user_id] = lambda: user_id
        yield client
        app.dependency_overrides = {}

@pytest.fixture
async def non_recruiter_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with get_new_db_connection() as conn:
            cursor = await conn.cursor()
            user_data, _ = await insert_or_return_user(cursor, "nonrecruiter@example.com", "Non", "Recruiter")
            await conn.commit()
            user_id = user_data["id"]

            org_data = CreateOrganizationRequest(name="Non Recruiter Org", slug="non-recruiter-org", user_id=user_id)
            new_org = await create_organization(cursor, org_data)
            await add_user_to_organization(cursor, user_id, new_org["id"], "MEMBER") # Member role
            await conn.commit()
        
        app.dependency_overrides[get_current_user_id] = lambda: user_id
        yield client
        app.dependency_overrides = {}

@pytest.fixture
async def setup_matching_data():
    async with get_new_db_connection() as conn:
        # Create a user who will post the job (admin/recruiter)
        job_poster_data, _ = await insert_or_return_user(conn.cursor(), "jobposter@example.com", "Job", "Poster")
        await conn.commit()
        job_poster_id = job_poster_data["id"]

        # Create an organization for the job
        org_data = CreateOrganizationRequest(name="Matching Org", slug="matching-org", user_id=job_poster_id)
        matching_org = await create_organization(conn.cursor(), org_data)
        await add_user_to_organization(conn.cursor(), job_poster_id, matching_org["id"], "ADMIN")
        await conn.commit()

        # Create some skills
        skill_python = await create_skill(NewSkill(new_name="Python", new_category="Programming"))
        skill_sql = await create_skill(NewSkill(new_name="SQL", new_category="Databases"))
        skill_ml = await create_skill(NewSkill(new_name="Machine Learning", new_category="AI"))
        await conn.commit()

        # Create a job posting with required skills
        job_data = NewJobPostingCreate(
            new_org_id=matching_org["id"],
            new_title="Data Scientist Position",
            new_description="Requires strong Python, SQL, and ML skills.",
            new_location="Remote",
            new_job_type="FULL_TIME",
            required_skills=[
                {"skill_id": skill_python.new_id, "threshold": 80},
                {"skill_id": skill_sql.new_id, "threshold": 70},
                {"skill_id": skill_ml.new_id, "threshold": 90},
            ]
        )
        test_job_posting = await create_job_posting(job_data, job_poster_id)
        await conn.commit()

        # Create matching candidates
        candidate1_data, _ = await insert_or_return_user(conn.cursor(), "candidate1@example.com", "Candidate", "One")
        await conn.commit()
        candidate1_id = candidate1_data["id"]
        await create_candidate_profile(conn, candidate1_id)
        await create_or_update_candidate_skill(candidate1_id, skill_python.new_id, 85)
        await create_or_update_candidate_skill(candidate1_id, skill_sql.new_id, 75)
        await create_or_update_candidate_skill(candidate1_id, skill_ml.new_id, 95)
        await conn.commit()

        # Create non-matching candidate (missing a skill)
        candidate2_data, _ = await insert_or_return_user(conn.cursor(), "candidate2@example.com", "Candidate", "Two")
        await conn.commit()
        candidate2_id = candidate2_data["id"]
        await create_candidate_profile(conn, candidate2_id)
        await create_or_update_candidate_skill(candidate2_id, skill_python.new_id, 90)
        await create_or_update_candidate_skill(candidate2_id, skill_sql.new_id, 60) # Below threshold
        await conn.commit()

        # Create non-matching candidate (no skills)
        candidate3_data, _ = await insert_or_return_user(conn.cursor(), "candidate3@example.com", "Candidate", "Three")
        await conn.commit()
        candidate3_id = candidate3_data["id"]
        await create_candidate_profile(conn, candidate3_id)
        await conn.commit()

        yield test_job_posting, matching_org["id"], job_poster_id, candidate1_id, candidate2_id, candidate3_id

@pytest.mark.asyncio
async def test_create_job_posting(auth_client: AsyncClient):
    # This test assumes the auth_client fixture sets up a recruiter user in org_id=1
    job_data = {
        "new_org_id": 1,
        "new_title": "Senior Software Engineer",
        "new_description": "Lead a team of engineers.",
        "new_location": "Remote",
        "new_job_type": "FULL_TIME"
    }
    response = await auth_client.post("/jobs/", json=job_data)
    assert response.status_code == 200
    assert response.json()["new_title"] == job_data["new_title"]
    assert response.json()["new_status"] == "OPEN"

@pytest.mark.asyncio
async def test_create_job_posting_unauthorized(auth_client: AsyncClient):
    # Override dependency to simulate a non-recruiter user
    app.dependency_overrides[get_current_user_id] = lambda: 999 # Non-existent user

    job_data = {
        "new_org_id": 1,
        "new_title": "Junior Developer",
        "new_description": "",
        "new_location": "",
        "new_job_type": "INTERNSHIP"
    }
    response = await auth_client.post("/jobs/", json=job_data)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to create job postings in this organization."

    app.dependency_overrides = {}

# More tests for GET, PUT (status), POST applications can be added similarly

@pytest.mark.asyncio
async def test_get_job_matches_authorized(recruiter_client: AsyncClient, setup_matching_data):
    job_posting, org_id, job_poster_id, candidate1_id, _, _ = await setup_matching_data

    # Override dependency to ensure the recruiter client is associated with the correct org
    app.dependency_overrides[get_current_user_id] = lambda: job_poster_id

    response = await recruiter_client.get(f"/jobs/{job_posting.new_id}/matches?org_id={org_id}")
    assert response.status_code == 200
    matches = response.json()

    assert len(matches) == 1
    assert matches[0]["user_id"] == candidate1_id
    assert matches[0]["match_score"] > 0

    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_job_matches_unauthorized_role(non_recruiter_client: AsyncClient, setup_matching_data):
    job_posting, org_id, _, _, _, _ = await setup_matching_data

    response = await non_recruiter_client.get(f"/jobs/{job_posting.new_id}/matches?org_id={org_id}")
    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have permission to perform this action."

@pytest.mark.asyncio
async def test_get_job_matches_unauthorized_org(recruiter_client: AsyncClient, setup_matching_data):
    job_posting, _, job_poster_id, _, _, _ = await setup_matching_data

    # Simulate a recruiter from a different organization
    app.dependency_overrides[get_current_user_id] = lambda: job_poster_id # Keep the same user, but change org context

    response = await recruiter_client.get(f"/jobs/{job_posting.new_id}/matches?org_id=999") # Wrong org_id
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to view matches for this job."

    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_job_matches_no_job_found(recruiter_client: AsyncClient, setup_matching_data):
    _, org_id, job_poster_id, _, _, _ = await setup_matching_data

    app.dependency_overrides[get_current_user_id] = lambda: job_poster_id
    response = await recruiter_client.get(f"/jobs/9999/matches?org_id={org_id}") # Non-existent job
    assert response.status_code == 404
    assert response.json()["detail"] == "Job posting not found."
    app.dependency_overrides = {}