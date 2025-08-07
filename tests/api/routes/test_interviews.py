import pytest
from httpx import AsyncClient
from main import app
from api.db import init_db
from api.db.user import insert_or_return_user, create_candidate_profile
from api.db.org import create_organization, add_user_to_organization
from api.db.job_posting_db import create_job_posting
from api.db.application_db import create_application
from api.db.interview_db import schedule_interview
from api.models import UserLoginData, CreateOrganizationRequest, NewJobPostingCreate, NewApplicationCreate, NewInterviewCreate, NewInterviewFeedbackCreate
from datetime import datetime, timedelta

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db.init_db() # Ensure the database is initialized before each test

@pytest.fixture
async def recruiter_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with init_db.get_new_db_connection() as conn:
            cursor = await conn.cursor()
            user_data, _ = await insert_or_return_user(cursor, "interviewer@example.com", "Interviewer", "User")
            await conn.commit()
            user_id = user_data["id"]

            org_data = CreateOrganizationRequest(name="Interview Org", slug="interview-org", user_id=user_id)
            new_org = await create_organization(cursor, org_data)
            await add_user_to_organization(cursor, user_id, new_org["id"], "RECRUITER")
            await conn.commit()
        
        app.dependency_overrides[get_current_user_id] = lambda: user_id
        yield client
        app.dependency_overrides = {}

@pytest.fixture
async def non_recruiter_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with init_db.get_new_db_connection() as conn:
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
async def test_job_and_application():
    async with init_db.get_new_db_connection() as conn:
        cursor = await conn.cursor()
        # Create a user for the job posting
        posted_by_user_data, _ = await insert_or_return_user(cursor, "jobposter@example.com", "Job", "Poster")
        await conn.commit()
        posted_by_user_id = posted_by_user_data["id"]

        # Create an organization for the job posting
        org_data = CreateOrganizationRequest(name="Job Org", slug="job-org", user_id=posted_by_user_id)
        new_org = await create_organization(cursor, org_data)
        await add_user_to_organization(cursor, posted_by_user_id, new_org["id"], "ADMIN")
        await conn.commit()

        # Create a job posting
        job_data = NewJobPostingCreate(
            new_org_id=new_org["id"],
            new_title="Test Interview Job",
            new_description="",
            new_location="Remote",
            new_job_type="FULL_TIME"
        )
        job_posting = await create_job_posting(job_data, posted_by_user_id)

        # Create a candidate user
        candidate_user_data, _ = await insert_or_return_user(cursor, "interviewcandidate@example.com", "Interview", "Candidate")
        await conn.commit()
        candidate_user_id = candidate_user_data["id"]
        await create_candidate_profile(candidate_user_id)

        # Create an application
        application_data = NewApplicationCreate(
            new_user_id=candidate_user_id,
            new_job_posting_id=job_posting.new_id
        )
        application = await create_application(application_data)
        return application, posted_by_user_id # Return application and user who posted job for auth checks

@pytest.mark.asyncio
async def test_schedule_interview_authorized(recruiter_client: AsyncClient, test_job_and_application):
    application, _ = await test_job_and_application
    scheduled_time = datetime.now() + timedelta(days=7)
    interview_data = NewInterviewCreate(
        new_application_id=application.new_id,
        new_scheduled_time=scheduled_time.isoformat(),
        new_duration_minutes=60,
        new_location_or_link="Zoom Link"
    )

    response = await recruiter_client.post("/interviews/", json=interview_data.dict())
    assert response.status_code == 200
    assert response.json()["new_application_id"] == application.new_id
    assert response.json()["new_status"] == "SCHEDULED"

@pytest.mark.asyncio
async def test_schedule_interview_unauthorized(non_recruiter_client: AsyncClient, test_job_and_application):
    application, _ = await test_job_and_application
    scheduled_time = datetime.now() + timedelta(days=7)
    interview_data = NewInterviewCreate(
        new_application_id=application.new_id,
        new_scheduled_time=scheduled_time.isoformat(),
        new_duration_minutes=60,
        new_location_or_link="Zoom Link"
    )

    response = await non_recruiter_client.post("/interviews/", json=interview_data.dict())
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to schedule interviews."

@pytest.mark.asyncio
async def test_submit_interview_feedback_authorized(recruiter_client: AsyncClient, test_job_and_application):
    application, interviewer_user_id = await test_job_and_application
    # Schedule an interview first
    scheduled_time = datetime.now() + timedelta(days=1)
    interview_data = NewInterviewCreate(
        new_application_id=application.new_id,
        new_scheduled_time=scheduled_time,
    )
    new_interview_db_obj = await schedule_interview(interview_data)

    feedback_data = NewInterviewFeedbackCreate(
        new_interview_id=new_interview_db_obj.new_id,
        new_interviewer_user_id=interviewer_user_id, # This user is the recruiter/admin
        new_overall_rating=5,
        new_feedback_for_candidate="Excellent candidate.",
        new_internal_notes="Hire immediately.",
        new_hiring_decision="SELECT"
    )
    response = await recruiter_client.post(f"/interviews/{new_interview_db_obj.new_id}/feedback", json=feedback_data.dict())
    assert response.status_code == 200
    assert response.json()["new_interview_id"] == new_interview_db_obj.new_id
    assert response.json()["new_hiring_decision"] == "SELECT"

@pytest.mark.asyncio
async def test_submit_interview_feedback_unauthorized(non_recruiter_client: AsyncClient, test_job_and_application):
    application, interviewer_user_id = await test_job_and_application
    # Schedule an interview first
    scheduled_time = datetime.now() + timedelta(days=1)
    interview_data = NewInterviewCreate(
        new_application_id=application.new_id,
        new_scheduled_time=scheduled_time,
    )
    new_interview_db_obj = await schedule_interview(interview_data)

    feedback_data = NewInterviewFeedbackCreate(
        new_interview_id=new_interview_db_obj.new_id,
        new_interviewer_user_id=interviewer_user_id, # This user is the recruiter/admin
        new_overall_rating=2,
        new_feedback_for_candidate="Poor fit.",
        new_internal_notes="",
        new_hiring_decision="REJECT"
    )
    response = await non_recruiter_client.post(f"/interviews/{new_interview_db_obj.new_id}/feedback", json=feedback_data.dict())
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to submit feedback."