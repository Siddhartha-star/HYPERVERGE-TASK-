import pytest
from datetime import datetime, timedelta
from api.db import interview_db, init_db, application_db, job_posting_db
from api.models import NewInterviewCreate, NewInterviewFeedbackCreate, NewJobPostingCreate, NewApplicationCreate

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db.init_db() # Ensure the database is initialized before each test

@pytest.fixture
async def create_test_job_and_application():
    # Create a job posting
    job_data = NewJobPostingCreate(
        new_org_id=1,
        new_title="Interview Job",
        new_description="",
        new_location="",
        new_job_type="FULL_TIME"
    )
    posted_by_user_id = 1
    job_posting = await job_posting_db.create_job_posting(job_data, posted_by_user_id)

    # Create an application for the job
    application_data = NewApplicationCreate(
        new_user_id=2, # Assuming user 2 is the candidate
        new_job_posting_id=job_posting.new_id
    )
    application = await application_db.create_application(application_data)
    return job_posting, application

@pytest.mark.asyncio
async def test_schedule_interview(create_test_job_and_application):
    job_posting, application = await create_test_job_and_application
    
    scheduled_time = datetime.now() + timedelta(days=7)
    interview_data = NewInterviewCreate(
        new_application_id=application.new_id,
        new_scheduled_time=scheduled_time,
        new_duration_minutes=90,
        new_location_or_link="Zoom Link"
    )
    new_interview = await interview_db.schedule_interview(interview_data)

    assert new_interview is not None
    assert new_interview.new_id is not None
    assert new_interview.new_application_id == application.new_id
    assert new_interview.new_status == "SCHEDULED"
    assert new_interview.new_scheduled_time.year == scheduled_time.year
    assert new_interview.new_scheduled_time.month == scheduled_time.month
    assert new_interview.new_scheduled_time.day == scheduled_time.day
    assert new_interview.new_duration_minutes == 90
    assert new_interview.new_location_or_link == "Zoom Link"

@pytest.mark.asyncio
async def test_get_interview_details(create_test_job_and_application):
    job_posting, application = await create_test_job_and_application
    
    scheduled_time = datetime.now() + timedelta(days=7)
    interview_data = NewInterviewCreate(
        new_application_id=application.new_id,
        new_scheduled_time=scheduled_time,
        new_duration_minutes=60,
        new_location_or_link="Google Meet"
    )
    new_interview = await interview_db.schedule_interview(interview_data)

    fetched_interview = await interview_db.get_interview_details(new_interview.new_id)
    assert fetched_interview is not None
    assert fetched_interview.new_id == new_interview.new_id
    assert fetched_interview.new_application_id == new_interview.new_application_id

    non_existent_interview = await interview_db.get_interview_details(9999)
    assert non_existent_interview is None

@pytest.mark.asyncio
async def test_add_interviewer(create_test_job_and_application):
    job_posting, application = await create_test_job_and_application

    interview_data = NewInterviewCreate(
        new_application_id=application.new_id,
        new_scheduled_time=datetime.now(),
    )
    new_interview = await interview_db.schedule_interview(interview_data)

    interviewer_user_id = 3 # Assuming user with ID 3 exists
    success = await interview_db.add_interviewer(new_interview.new_id, interviewer_user_id)
    assert success is True

    # Test adding same interviewer again (should return False)
    success_again = await interview_db.add_interviewer(new_interview.new_id, interviewer_user_id)
    assert success_again is False

@pytest.mark.asyncio
async def test_submit_interview_feedback(create_test_job_and_application):
    job_posting, application = await create_test_job_and_application

    interview_data = NewInterviewCreate(
        new_application_id=application.new_id,
        new_scheduled_time=datetime.now(),
    )
    new_interview = await interview_db.schedule_interview(interview_data)

    feedback_data = NewInterviewFeedbackCreate(
        new_interview_id=new_interview.new_id,
        new_interviewer_user_id=3,
        new_overall_rating=4,
        new_feedback_for_candidate="Good communication.",
        new_internal_notes="Strong potential.",
        new_hiring_decision="SELECT"
    )
    new_feedback = await interview_db.submit_interview_feedback(feedback_data)

    assert new_feedback is not None
    assert new_feedback.new_id is not None
    assert new_feedback.new_interview_id == new_interview.new_id
    assert new_feedback.new_interviewer_user_id == 3
    assert new_feedback.new_hiring_decision == "SELECT"