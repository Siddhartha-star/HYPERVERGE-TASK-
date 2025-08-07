import pytest
from datetime import datetime
from api.db import job_posting_db, init_db
from api.models import NewJobPostingCreate, NewJobPostingRead

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db.init_db() # Ensure the database is initialized before each test

@pytest.mark.asyncio
async def test_create_job_posting():
    # Test creating a new job posting
    job_data = NewJobPostingCreate(
        new_org_id=1,
        new_title="Software Engineer",
        new_description="Develop and maintain software.",
        new_location="Remote",
        new_job_type="FULL_TIME"
    )
    posted_by_user_id = 1 # Assuming a user with ID 1 exists
    new_job = await job_posting_db.create_job_posting(job_data, posted_by_user_id)

    assert new_job is not None
    assert new_job.new_id is not None
    assert new_job.new_org_id == job_data.new_org_id
    assert new_job.new_title == job_data.new_title
    assert new_job.new_posted_by_user_id == posted_by_user_id
    assert new_job.new_status == "OPEN"

@pytest.mark.asyncio
async def test_get_job_posting_by_id():
    # Create a job posting first
    job_data = NewJobPostingCreate(
        new_org_id=1,
        new_title="Data Scientist",
        new_description="Analyze data.",
        new_location="On-site",
        new_job_type="FULL_TIME"
    )
    posted_by_user_id = 1
    new_job = await job_posting_db.create_job_posting(job_data, posted_by_user_id)

    fetched_job = await job_posting_db.get_job_posting_by_id(new_job.new_id)
    assert fetched_job is not None
    assert fetched_job.new_id == new_job.new_id
    assert fetched_job.new_title == new_job.new_title

    # Test with non-existent ID
    non_existent_job = await job_posting_db.get_job_posting_by_id(9999)
    assert non_existent_job is None

@pytest.mark.asyncio
async def test_get_job_postings_for_org():
    org_id = 1
    posted_by_user_id = 1

    # Create multiple job postings for the same organization
    await job_posting_db.create_job_posting(
        NewJobPostingCreate(new_org_id=org_id, new_title="Job 1", new_description="", new_location="", new_job_type="FULL_TIME"), posted_by_user_id
    )
    await job_posting_db.create_job_posting(
        NewJobPostingCreate(new_org_id=org_id, new_title="Job 2", new_description="", new_location="", new_job_type="INTERNSHIP"), posted_by_user_id
    )
    await job_posting_db.create_job_posting(
        NewJobPostingCreate(new_org_id=2, new_title="Job for another org", new_description="", new_location="", new_job_type="FULL_TIME"), 2 # Another org
    )

    jobs = await job_posting_db.get_job_postings_for_org(org_id)
    assert len(jobs) == 2
    assert all(job.new_org_id == org_id for job in jobs)

@pytest.mark.asyncio
async def test_update_job_posting_status():
    job_data = NewJobPostingCreate(
        new_org_id=1,
        new_title="Job to Update",
        new_description="",
        new_location="",
        new_job_type="FULL_TIME"
    )
    posted_by_user_id = 1
    new_job = await job_posting_db.create_job_posting(job_data, posted_by_user_id)

    updated = await job_posting_db.update_job_posting_status(new_job.new_id, "CLOSED")
    assert updated is True
    fetched_job = await job_posting_db.get_job_posting_by_id(new_job.new_id)
    assert fetched_job.new_status == "CLOSED"

    # Test updating non-existent job
    updated_non_existent = await job_posting_db.update_job_posting_status(9999, "CLOSED")
    assert updated_non_existent is False