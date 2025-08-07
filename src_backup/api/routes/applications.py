from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from api.models import NewApplicationRead, NewApplicationCreate
from api.db import application_db, job_posting_db
from api.db.user import get_user_organizations_with_roles, get_user_role_in_org
from api.utils.security import get_current_user_id
from api.utils.db import get_new_db_connection

router = APIRouter(prefix="/applications", tags=["Applications"])

@router.post("/", response_model=NewApplicationRead)
async def submit_application(application_data: NewApplicationCreate, user_id: int = Depends(get_current_user_id)):
    # This endpoint is for candidates to submit applications
    # Authorization: Requires a logged-in user with a 'CANDIDATE' profile.
    # For simplicity, assuming any logged in user can apply. For a real system, you'd verify candidate profile existence.
    
    # Ensure the job posting exists
    job_posting = await job_posting_db.get_job_posting_by_id(application_data.new_job_posting_id)
    if not job_posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting not found.")

    # Check if user has already applied
    existing_application = await application_db.get_application_for_user_and_job(user_id, application_data.new_job_posting_id)
    if existing_application:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already applied to this job.")

    async with get_new_db_connection() as conn:
        new_application = await application_db.create_application(conn, user_id, application_data.new_job_posting_id)
        await conn.commit()

    if not new_application:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to submit application.")
    return new_application


@router.get("/me", response_model=List[NewApplicationRead])
async def get_my_applications(user_id: int = Depends(get_current_user_id)):
    applications = await application_db.get_applications_for_user(user_id)
    return applications

@router.get("/{app_id}", response_model=NewApplicationRead)
async def get_application_details(app_id: int, user_context: dict = Depends(get_current_user_id)):
    user_id = user_context.get("id")
    async with get_new_db_connection() as conn:
        application = await application_db.get_application_details_from_db(conn, app_id)
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
        
        job_posting_org_id = application.job_posting.new_org_id
        user_role = await get_user_role_in_org(conn, user_id, job_posting_org_id)

        if user_id == application.new_user_id or (user_role in ["ADMIN", "RECRUITER", "HIRING_MANAGER"]):
            return application
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this application.")

@router.put("/{app_id}/status", response_model=bool)
async def update_application_status(app_id: int, status_update: str, user_context: dict = Depends(get_current_user_id)):
    user_id = user_context.get("id")
    async with get_new_db_connection() as conn:
        application = await application_db.get_application_details_from_db(conn, app_id)
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

        job_posting_org_id = application.job_posting.new_org_id
        user_role = await get_user_role_in_org(conn, user_id, job_posting_org_id)
        
        if not (user_role in ["ADMIN", "RECRUITER", "HIRING_MANAGER"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update application status.")

        success = await application_db.update_application_status(app_id, status_update)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update application status.")
        return success