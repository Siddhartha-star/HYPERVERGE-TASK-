import pytest
from httpx import AsyncClient
from main import app
from api.db import init_db
from api.db.user import insert_or_return_user, create_candidate_profile
from api.db.org import create_organization, add_user_to_organization
from api.models import CreateOrganizationRequest, NewCandidateProfileUpdate, NewCandidateProfileRead
from api.utils.auth import get_current_user_id
from api.utils.db import get_new_db_connection

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db.init_db() # Ensure the database is initialized before each test

@pytest.fixture
async def candidate_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with get_new_db_connection() as conn:
            user_data, _ = await insert_or_return_user(conn.cursor(), "candidate@example.com", "Candidate", "User")
            await conn.commit()
            user_id = user_data["id"]
            await create_candidate_profile(conn, user_id)
            await conn.commit()

            # Create an organization and add the candidate as 'CANDIDATE' role
            org_data = CreateOrganizationRequest(name="Candidate Org", slug="candidate-org", user_id=user_id)
            new_org = await create_organization(conn.cursor(), org_data)
            await add_user_to_organization(conn.cursor(), user_id, new_org["id"], "CANDIDATE")
            await conn.commit()
        
        app.dependency_overrides[get_current_user_id] = lambda: user_id
        yield client
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_update_my_candidate_profile(candidate_client: AsyncClient):
    profile_data = {
        "new_phone_number": "123-456-7890",
        "new_location": "Remote, USA",
        "new_bio": "Experienced software engineer.",
        "new_resume_url": "http://example.com/resume.pdf",
        "new_linkedin_profile": "http://linkedin.com/in/candidate",
        "new_portfolio_url": "http://example.com/portfolio"
    }

    response = await candidate_client.put("/profiles/me", json=profile_data)

    assert response.status_code == 200
    updated_profile = response.json()
    assert updated_profile["new_phone_number"] == profile_data["new_phone_number"]
    assert updated_profile["new_location"] == profile_data["new_location"]
    assert updated_profile["new_bio"] == profile_data["new_bio"]

@pytest.mark.asyncio
async def test_get_my_candidate_profile(candidate_client: AsyncClient):
    response = await candidate_client.get("/profiles/me")
    assert response.status_code == 200
    profile = response.json()
    assert profile["new_user_id"] is not None
    assert profile["new_status"] == "ACTIVE"

    # Test when profile doesn't exist (simulated by non-existent user_id)
    app.dependency_overrides[get_current_user_id] = lambda: 9999
    response_non_existent = await candidate_client.get("/profiles/me")
    assert response_non_existent.status_code == 404
    assert response_non_existent.json()["detail"] == "Candidate profile not found."

    app.dependency_overrides = {}