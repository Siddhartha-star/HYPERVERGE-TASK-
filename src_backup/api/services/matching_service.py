import sqlite3
from typing import List, Dict, Optional
from api.utils.db import get_new_db_connection

async def find_matching_candidates(conn: sqlite3.Connection, job_id: int) -> List[Dict]:
    """
    Finds candidates that match the required skills and proficiency thresholds for a given job.
    Returns a list of candidates ordered by a match score (sum of proficiency scores for required skills).
    """
    cursor = await conn.cursor()

    # 1. Fetch Job Requirements
    await cursor.execute(
        """SELECT NEW_skill_id, NEW_required_proficiency_threshold FROM NEW_job_required_skills WHERE NEW_job_posting_id = ?""",
        (job_id,)
    )
    required_skills = await cursor.fetchall()
    if not required_skills:
        return [] # No skills required for this job, so no matches

    required_skill_map = {skill_id: threshold for skill_id, threshold in required_skills}
    required_skill_ids = tuple(required_skill_map.keys())

    # 2. Find Candidates with relevant skills and their proficiencies
    # Select users who have at least one of the required skills
    # We'll filter for all required skills in Python for simplicity, more complex SQL JOINs can be used for performance
    query = f"""SELECT
                cs.NEW_user_id, u.first_name, u.last_name, u.email, cp.NEW_bio, cp.NEW_resume_url, cp.NEW_linkedin_profile,
                GROUP_CONCAT(cs.NEW_skill_id || ':' || cs.NEW_proficiency_score) AS candidate_skills_str
                FROM NEW_candidate_skills cs
                JOIN users u ON cs.NEW_user_id = u.id
                LEFT JOIN NEW_candidate_profiles cp ON cs.NEW_user_id = cp.NEW_user_id
                WHERE cs.NEW_skill_id IN ({','.join(['?' for _ in required_skill_ids])})
                GROUP BY cs.NEW_user_id
            """
    await cursor.execute(query, required_skill_ids)
    candidate_rows = await cursor.fetchall()

    matching_candidates = []

    for row in candidate_rows:
        candidate_id = row[0]
        candidate_skills_str = row[7]

        candidate_skills = {}
        if candidate_skills_str:
            for skill_str in candidate_skills_str.split(','):
                skill_id, proficiency = map(int, skill_str.split(':'))
                candidate_skills[skill_id] = proficiency
        
        # 3. Filter and Rank
        has_all_required_skills = True
        total_proficiency_score = 0

        for req_skill_id, req_threshold in required_skill_map.items():
            if req_skill_id not in candidate_skills or candidate_skills[req_skill_id] < req_threshold:
                has_all_required_skills = False
                break
            total_proficiency_score += candidate_skills[req_skill_id]

        if has_all_required_skills:
            matching_candidates.append({
                "user_id": candidate_id,
                "first_name": row[1],
                "last_name": row[2],
                "email": row[3],
                "bio": row[4],
                "resume_url": row[5],
                "linkedin_profile": row[6],
                "match_score": total_proficiency_score, # Simple sum of proficiencies as match score
                "skills_matched": candidate_skills # Include all matched skills for debugging/richer display
            })
    
    # Order by match score descending
    matching_candidates.sort(key=lambda x: x["match_score"], reverse=True)

    return matching_candidates