from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict
from api.db.user import get_candidate_profile_by_user_id
from api.models import CandidateProfile
from api.utils.security import get_current_user_id

router = APIRouter()

@router.put("/me", response_model=NewCandidateProfileRead)
async def update_my_candidate_profile(profile_data: NewCandidateProfileUpdate, user_context: dict = Depends(get_current_user)):
    user_id = user_context.get("id")
    async with get_new_db_connection() as conn:
        updated_profile = await update_candidate_profile(conn, user_id, profile_data)
        await conn.commit()
    if not updated_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate profile not found or no changes applied.")
    return updated_profile

@router.get("/me", response_model=NewCandidateProfileRead)
async def get_my_candidate_profile(user_id: int = Depends(get_current_user_id)):
    profile = await get_candidate_profile(user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate profile not found.")
    return profile