from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict
from api.db.job_posting_db import ( # type: ignore
    get_job_posting_by_id, update_job_posting_status
)
from api.db import job_posting_db, application_db # type: ignore
from api.db.user import get_user_organizations_with_roles
from api.models import JobPostingStatusUpdate, NewJobPostingRead, NewJobPostingCreate, NewApplicationRead
from api.utils.security import get_current_user_id
from api.utils.security import role_checker
from api.utils.db import get_new_db_connection
from api.services import matching_service

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("/", response_model=NewJobPostingRead, dependencies=[Depends(role_checker(["ADMIN", "RECRUITER", "HIRING_MANAGER"]))])
async def create_job(job_posting: NewJobPostingCreate, user_id_org_id: tuple = Depends(role_checker(["ADMIN", "RECRUITER", "HIRING_MANAGER"]))) :
    user_id, org_id = user_id_org_id # Unpack the tuple from role_checker
    if org_id != job_posting.new_org_id: # Ensure the job is created for the authorized organization
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create job postings in this organization.")

    new_job = await job_posting_db.create_job_posting(job_posting, user_id)
    if not new_job:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create job posting.")
    return new_job

@router.get("/{job_id}", response_model=NewJobPostingRead)
async def get_job_by_id(job_id: int, user_id: int = Depends(get_current_user_id)):
    job_posting = await job_posting_db.get_job_posting_by_id(job_id)
    if not job_posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting not found.")
    
    # Authorization: Any user can view job postings if it's open
    return job_posting

@router.get("/", response_model=List[NewJobPostingRead])
async def get_all_jobs(org_id: int, user_id_org_id: tuple = Depends(role_checker(["ADMIN", "RECRUITER", "HIRING_MANAGER", "MEMBER", "CANDIDATE"]))):
    user_id, authorized_org_id = user_id_org_id
    if org_id != authorized_org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view jobs in this organization.")

    jobs = await job_posting_db.get_open_job_postings_for_org(org_id)
    return jobs

@router.put("/{job_id}/status", response_model=bool)
async def update_job_status(job_id: int, status_update: JobPostingStatusUpdate, user_id_org_id: tuple = Depends(role_checker(["ADMIN", "RECRUITER", "HIRING_MANAGER"]))):
    user_id, org_id = user_id_org_id
    job_posting = await get_job_posting_by_id(job_id)
    if not job_posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting not found.")

    # Re-using the role_checker by passing the org_id from the job_posting
    # This part will require further refinement to properly integrate role_checker
    # for path parameters. For now, it's a placeholder for the logic.
    user_roles = await get_user_organizations_with_roles(user_id, job_posting.new_org_id)
    if not user_roles or not any(role in ["ADMIN", "RECRUITER", "HIRING_MANAGER"] for role in user_roles.values()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update job posting status.")

    success = await update_job_posting_status(job_id, status_update.new_status)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update job posting status.")
    return success

@router.post("/{job_id}/applications", response_model=NewApplicationRead)
async def apply_to_job(job_id: int, user_id: int = Depends(get_current_user_id)):
    job_posting = await job_posting_db.get_job_posting_by_id(job_id)
    if not job_posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting not found.")

    existing_application = await application_db.get_application_for_user_and_job(user_id, job_id)
    if existing_application:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already applied to this job.")

    # Check if the user is a CANDIDATE or has a candidate profile. This requires fetching candidate profile
    # For simplicity, assuming any logged in user can apply. For a real system, you'd verify candidate profile existence.
    async with get_new_db_connection() as conn:
        new_application = await application_db.create_application(conn, user_id, job_id)
    if not new_application:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to submit application.")
    return new_application

@router.get("/{job_id}/applications", response_model=List[NewApplicationRead])
async def get_job_applications(job_id: int, user_id_org_id: tuple = Depends(role_checker(["ADMIN", "RECRUITER", "HIRING_MANAGER"]))):
    user_id, org_id = user_id_org_id
    job_posting = await job_posting_db.get_job_posting_by_id(job_id)
    if not job_posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting not found.")
    
    if org_id != job_posting.new_org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view applications for this job.")

    applications = await application_db.get_applications_for_job(job_id)
    return applications

@router.get("/{job_id}/matches", response_model=List[Dict])
async def get_job_matches(job_id: int, user_id_org_id: tuple = Depends(role_checker(["ADMIN", "RECRUITER", "HIRING_MANAGER"]))):
    user_id, org_id = user_id_org_id
    job_posting = await job_posting_db.get_job_posting_by_id(job_id)
    if not job_posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting not found.")
    
    if org_id != job_posting.new_org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view matches for this job.")

    async with get_new_db_connection() as conn:
        matches = await matching_service.find_matching_candidates(conn, job_id)
    return matches