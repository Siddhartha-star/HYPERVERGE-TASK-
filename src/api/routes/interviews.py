from fastapi import APIRouter, Depends, HTTPException, status
from api.models import NewInterviewCreate, NewInterviewFeedbackCreate, NewInterviewRead, NewInterviewFeedbackRead
from api.db import interview_db, application_db, job_posting_db
from api.db.user import get_user_organizations_with_roles
from api.utils.security import get_current_user_id

router = APIRouter(prefix="/interviews", tags=["Interviews"])

@router.post("/", response_model=NewInterviewRead)
async def schedule_new_interview(interview_data: NewInterviewCreate, user_id: int = Depends(get_current_user_id)):
    application = await application_db.get_application_for_user_and_job(interview_data.new_application_id, user_id) # Placeholder, needs to be get by app_id
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    job_posting = await job_posting_db.get_job_posting_by_id(application.new_job_posting_id)
    if not job_posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated job posting not found.")

    user_roles = await get_user_organizations_with_roles(user_id, job_posting.new_org_id)
    if not user_roles or not any(role in ["ADMIN", "RECRUITER"] for role in user_roles.values()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to schedule interviews.")
    
    new_interview = await interview_db.schedule_interview(interview_data)
    if not new_interview:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to schedule interview.")
    return new_interview

@router.post("/{interview_id}/feedback", response_model=NewInterviewFeedbackRead)
async def submit_feedback(interview_id: int, feedback_data: NewInterviewFeedbackCreate, user_id: int = Depends(get_current_user_id)):
    interview = await interview_db.get_interview_details(interview_id)
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")
    
    # In a real scenario, you'd verify if the user is an assigned interviewer for this interview
    # For simplicity, checking if the user is an admin/recruiter in the org associated with the application
    application = await application_db.get_application_for_user_and_job(interview.new_application_id, user_id) # Placeholder
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated application not found.")

    job_posting = await job_posting_db.get_job_posting_by_id(application.new_job_posting_id)
    if not job_posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated job posting not found.")

    user_roles = await get_user_organizations_with_roles(user_id, job_posting.new_org_id)
    if not user_roles or not any(role in ["ADMIN", "RECRUITER", "HIRING_MANAGER"] for role in user_roles.values()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to submit feedback.")

    feedback = await interview_db.submit_interview_feedback(feedback_data)
    if not feedback:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to submit feedback.")
    return feedback