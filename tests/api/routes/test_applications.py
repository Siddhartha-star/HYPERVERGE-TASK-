import pytest
from httpx import AsyncClient
from main import app
from api.db import init_db
from api.db.user import insert_or_return_user, create_candidate_profile
from api.db.org import create_organization, add_user_to_organization
from api.db.job_posting_db import create_job_posting
from api.db.application_db import create_application
from api.models import UserLoginData, CreateOrganizationRequest, NewJobPostingCreate, NewApplicationCreate

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db.init_db() # Ensure the database is initialized before each test

@pytest.fixture
async def recruiter_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with init_db.get_new_db_connection() as conn:
            cursor = await conn.cursor()
            user_data, _ = await insert_or_return_user(cursor, "recruiter@example.com", "Recruiter", "User")
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
async def candidate_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with init_db.get_new_db_connection() as conn:
            cursor = await conn.cursor()
            user_data, _ = await insert_or_return_user(cursor, "candidate@example.com", "Candidate", "User")
            await conn.commit()
            user_id = user_data["id"]
            await create_candidate_profile(user_id)

            # Create an organization and add the candidate as 'CANDIDATE' role
            org_data = CreateOrganizationRequest(name="Candidate Org", slug="candidate-org", user_id=user_id)
            new_org = await create_organization(cursor, org_data)
            await add_user_to_organization(cursor, user_id, new_org["id"], "CANDIDATE")
            await conn.commit()
        
        app.dependency_overrides[get_current_user_id] = lambda: user_id
        yield client
        app.dependency_overrides = {}

@pytest.fixture
async def test_job_and_application(recruiter_client: AsyncClient):
    # Create a job posting using the recruiter client
    job_data = NewJobPostingCreate(
        new_org_id=1, # Assuming org_id=1 is created by recruiter_client fixture
        new_title="Software Engineer - Test",
        new_description="",
        new_location="Remote",
        new_job_type="FULL_TIME"
    )
    response = await recruiter_client.post("/jobs/", json=job_data.dict())
    job_posting = response.json()

    # Create an application by a candidate
    async with init_db.get_new_db_connection() as conn:
        cursor = await conn.cursor()
        user_data, _ = await insert_or_return_user(cursor, "applicant@example.com", "Applicant", "User")
        await conn.commit()
        candidate_user_id = user_data["id"]

        application_data = NewApplicationCreate(
            new_user_id=candidate_user_id,
            new_job_posting_id=job_posting["new_id"]
        )
        new_app = await create_application(application_data)

    return job_posting, new_app, candidate_user_id

@pytest.mark.asyncio
async def test_get_my_applications_candidate(candidate_client: AsyncClient, test_job_and_application):
    job_posting, application, candidate_user_id = await test_job_and_application
    
    # Override dependency to make sure we are testing with the correct candidate
    app.dependency_overrides[get_current_user_id] = lambda: candidate_user_id

    response = await candidate_client.get("/applications/")
    assert response.status_code == 200
    applications = response.json()
    assert len(applications) >= 1 # Could have other applications from other tests
    assert any(app["new_id"] == application.new_id for app in applications)

    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_application_details_candidate(candidate_client: AsyncClient, test_job_and_application):
    job_posting, application, candidate_user_id = await test_job_and_application

    app.dependency_overrides[get_current_user_id] = lambda: candidate_user_id

    response = await candidate_client.get(f"/applications/{application.new_id}")
    assert response.status_code == 200
    fetched_app = response.json()
    assert fetched_app["new_id"] == application.new_id

    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_application_details_recruiter(recruiter_client: AsyncClient, test_job_and_application):
    job_posting, application, candidate_user_id = await test_job_and_application

    response = await recruiter_client.get(f"/applications/{application.new_id}")
    assert response.status_code == 200
    fetched_app = response.json()
    assert fetched_app["new_id"] == application.new_id

@pytest.mark.asyncio
async def test_get_application_details_unauthorized(recruiter_client: AsyncClient, test_job_and_application):
    job_posting, application, candidate_user_id = await test_job_and_application

    # Simulate a user from a different organization or with no roles
    app.dependency_overrides[get_current_user_id] = lambda: 9999 # Non-existent user
    response = await recruiter_client.get(f"/applications/{application.new_id}")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to view this application."

    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_update_application_status_recruiter(recruiter_client: AsyncClient, test_job_and_application):
    job_posting, application, candidate_user_id = await test_job_and_application

    response = await recruiter_client.put(f"/applications/{application.new_id}/status", json="SHORTLISTED")
    assert response.status_code == 200
    assert response.json() is True

    # Verify status change
    fetched_app = await application_db.get_application_for_user_and_job(application.new_user_id, application.new_job_posting_id)
    assert fetched_app.new_status == "SHORTLISTED"

@pytest.mark.asyncio
async def test_update_application_status_unauthorized(candidate_client: AsyncClient, test_job_and_application):
    job_posting, application, candidate_user_id = await test_job_and_application
    
    # Candidate cannot update status
    app.dependency_overrides[get_current_user_id] = lambda: candidate_user_id
    response = await candidate_client.put(f"/applications/{application.new_id}/status", json="HIRED")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update application status."

    app.dependency_overrides = {}