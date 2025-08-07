import pytest
from datetime import datetime
from api.db import application_db, init_db, job_posting_db
from api.models import NewApplicationCreate, NewApplicationRead, NewJobPostingCreate

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db.init_db() # Ensure the database is initialized before each test

@pytest.fixture
async def create_test_job_posting():
    job_data = NewJobPostingCreate(
        new_org_id=1,
        new_title="Test Job for Application",
        new_description="",
        new_location="",
        new_job_type="FULL_TIME"
    )
    posted_by_user_id = 1
    return await job_posting_db.create_job_posting(job_data, posted_by_user_id)

@pytest.mark.asyncio
async def test_create_application(create_test_job_posting):
    job_posting = await create_test_job_posting
    user_id = 1 # Assuming user with ID 1 exists

    application_data = NewApplicationCreate(
        new_user_id=user_id,
        new_job_posting_id=job_posting.new_id
    )
    new_app = await application_db.create_application(application_data)

    assert new_app is not None
    assert new_app.new_id is not None
    assert new_app.new_user_id == user_id
    assert new_app.new_job_posting_id == job_posting.new_id
    assert new_app.new_status == "APPLIED"
    assert new_app.new_applied_at is not None

@pytest.mark.asyncio
async def test_get_application_for_user_and_job(create_test_job_posting):
    job_posting = await create_test_job_posting
    user_id = 1

    application_data = NewApplicationCreate(
        new_user_id=user_id,
        new_job_posting_id=job_posting.new_id
    )
    await application_db.create_application(application_data)

    fetched_app = await application_db.get_application_for_user_and_job(user_id, job_posting.new_id)
    assert fetched_app is not None
    assert fetched_app.new_user_id == user_id
    assert fetched_app.new_job_posting_id == job_posting.new_id

    non_existent_app = await application_db.get_application_for_user_and_job(9999, job_posting.new_id)
    assert non_existent_app is None

@pytest.mark.asyncio
async def test_update_application_status(create_test_job_posting):
    job_posting = await create_test_job_posting
    user_id = 1

    application_data = NewApplicationCreate(
        new_user_id=user_id,
        new_job_posting_id=job_posting.new_id
    )
    new_app = await application_db.create_application(application_data)

    updated = await application_db.update_application_status(new_app.new_id, "SHORTLISTED")
    assert updated is True

    fetched_app = await application_db.get_application_for_user_and_job(user_id, job_posting.new_id)
    assert fetched_app.new_status == "SHORTLISTED"

    updated_non_existent = await application_db.update_application_status(9999, "HIRED")
    assert updated_non_existent is False

@pytest.mark.asyncio
async def test_get_applications_for_job(create_test_job_posting):
    job_posting = await create_test_job_posting
    user_id_1 = 1
    user_id_2 = 2 # Assuming user with ID 2 exists

    await application_db.create_application(NewApplicationCreate(new_user_id=user_id_1, new_job_posting_id=job_posting.new_id))
    await application_db.create_application(NewApplicationCreate(new_user_id=user_id_2, new_job_posting_id=job_posting.new_id))

    applications = await application_db.get_applications_for_job(job_posting.new_id)
    assert len(applications) == 2
    assert all(app.new_job_posting_id == job_posting.new_id for app in applications)