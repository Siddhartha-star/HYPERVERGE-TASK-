from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict
from api.db.course import (
    create_course as create_course_in_db,
    get_all_courses_for_org as get_all_courses_for_org_from_db,
    delete_course as delete_course_in_db,
    get_cohorts_for_course as get_cohorts_for_course_from_db,
    get_tasks_for_course as get_tasks_for_course_from_db,
    update_course_name as update_course_name_in_db,
    add_tasks_to_courses as add_tasks_to_courses_in_db,
    remove_tasks_from_courses as remove_tasks_from_courses_in_db,
    update_task_orders as update_task_orders_in_db,
    add_milestone_to_course as add_milestone_to_course_in_db,
    update_milestone_orders as update_milestone_orders_in_db,
    get_course as get_course_from_db,
    swap_milestone_ordering_for_course as swap_milestone_ordering_for_course_in_db,
    swap_task_ordering_for_course as swap_task_ordering_for_course_in_db,
    get_course_org_id,
)
from api.db.cohort import (
    add_course_to_cohorts as add_course_to_cohorts_in_db,
    remove_course_from_cohorts as remove_course_from_cohorts_from_db,
)
from api.models import (
    CreateCourseRequest,
    RemoveCourseFromCohortsRequest,
    AddCourseToCohortsRequest,
    UpdateCourseNameRequest,
    AddTasksToCoursesRequest,
    RemoveTasksFromCoursesRequest,
    UpdateTaskOrdersRequest,
    UpdateMilestoneOrdersRequest,
    CreateCourseResponse,
    Course,
    CourseWithMilestonesAndTasks,
    AddMilestoneToCourseRequest,
    AddMilestoneToCourseResponse,
    SwapMilestoneOrderingRequest,
    SwapTaskOrderingRequest,
    CourseCohort,
)
from api.utils.security import role_checker
from api.db.milestone import get_milestone_org_id
from api.db.task import get_task_org_id, get_task_from_db
from api.db.cohort import get_cohort_org_id
from api.db.milestone import get_milestone_from_db

router = APIRouter()


@router.post("/{org_id}/", response_model=CreateCourseResponse)
async def create_course(org_id: int, request: CreateCourseRequest, user_id_org_id: tuple = Depends(role_checker(["ADMIN"]))) -> CreateCourseResponse:
    if org_id != request.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create courses in this organization.")
    return {"id": await create_course_in_db(request.name, request.org_id)}


@router.get("/{org_id}/", response_model=List[Course])
async def get_all_courses_for_org(org_id: int, user_id_org_id: tuple = Depends(role_checker(["ADMIN", "MEMBER", "RECRUITER", "HIRING_MANAGER", "CANDIDATE"]))) -> List[Course]:
    user_id, authorized_org_id = user_id_org_id
    if org_id != authorized_org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view courses in this organization.")
    return await get_all_courses_for_org_from_db(org_id)


@router.get("/{org_id}/{course_id}", response_model=CourseWithMilestonesAndTasks)
async def get_course(
    org_id: int, course_id: int, only_published: bool = True, user_id_org_id: tuple = Depends(role_checker(["ADMIN", "MEMBER", "RECRUITER", "HIRING_MANAGER", "CANDIDATE"]))
) -> CourseWithMilestonesAndTasks:
    user_id, authorized_org_id = user_id_org_id
    if org_id != authorized_org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this course.")
    return await get_course_from_db(course_id, only_published)


@router.post("/{org_id}/tasks", dependencies=[Depends(role_checker(["ADMIN"]))])
async def add_tasks_to_courses(org_id: int, request: AddTasksToCoursesRequest):
    for course_id, _, _ in request.course_tasks:
        course_org_id = await get_course_org_id(course_id)
        if course_org_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course not found in this organization.")

    await add_tasks_to_courses_in_db(request.course_tasks)
    return {"success": True}


@router.delete("/{org_id}/tasks", dependencies=[Depends(role_checker(["ADMIN"]))])
async def remove_tasks_from_courses(org_id: int, request: RemoveTasksFromCoursesRequest):
    for course_id, _ in request.course_tasks:
        course_org_id = await get_course_org_id(course_id)
        if course_org_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course not found in this organization.")

    await remove_tasks_from_courses_in_db(request.course_tasks)
    return {"success": True}


@router.put("/{org_id}/tasks/order", dependencies=[Depends(role_checker(["ADMIN"]))])
async def update_task_orders(org_id: int, request: UpdateTaskOrdersRequest):
    for task_id, _ in request.task_orders:
        task = await get_task_from_db(task_id)
        if task.org_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Task not found in this organization.")

    await update_task_orders_in_db(request.task_orders)
    return {"success": True}


@router.post("/{org_id}/{course_id}/milestones", response_model=AddMilestoneToCourseResponse, dependencies=[Depends(role_checker(["ADMIN"]))])
async def add_milestone_to_course(
    org_id: int, course_id: int, request: AddMilestoneToCourseRequest
) -> AddMilestoneToCourseResponse:
    course_org_id = await get_course_org_id(course_id)
    if course_org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course not found in this organization.")

    milestone_id, _ = await add_milestone_to_course_in_db(
        course_id,
        request.name,
        request.color,
    )
    return {"id": milestone_id}


@router.put("/{org_id}/milestones/order", dependencies=[Depends(role_checker(["ADMIN"]))])
async def update_milestone_orders(org_id: int, request: UpdateMilestoneOrdersRequest):
    for milestone_id, _ in request.milestone_orders:
        milestone = await get_milestone_from_db(milestone_id)
        if milestone.org_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Milestone not found in this organization.")

    await update_milestone_orders_in_db(request.milestone_orders)
    return {"success": True}


@router.delete("/{org_id}/{course_id}", dependencies=[Depends(role_checker(["ADMIN"]))])
async def delete_course(org_id: int, course_id: int):
    course_org_id = await get_course_org_id(course_id)
    if course_org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course not found in this organization.")

    await delete_course_in_db(course_id)
    return {"success": True}


@router.post("/{org_id}/{course_id}/cohorts", dependencies=[Depends(role_checker(["ADMIN"]))])
async def add_course_to_cohorts(org_id: int, course_id: int, request: AddCourseToCohortsRequest):
    course_org_id = await get_course_org_id(course_id)
    if course_org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course not found in this organization.")
    
    # Further authorization: ensure cohorts belong to the same organization
    for cohort_id in request.cohort_ids:
        cohort_org_id = await get_cohort_org_id(cohort_id)
        if cohort_org_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="One or more cohorts do not belong to this organization.")

    await add_course_to_cohorts_in_db(
        course_id,
        request.cohort_ids,
        is_drip_enabled=request.drip_config.is_drip_enabled,
        frequency_value=request.drip_config.frequency_value,
        frequency_unit=request.drip_config.frequency_unit,
        publish_at=request.drip_config.publish_at,
    )
    return {"success": True}


@router.delete("/{org_id}/{course_id}/cohorts", dependencies=[Depends(role_checker(["ADMIN"]))])
async def remove_course_from_cohorts(
    org_id: int, course_id: int, request: RemoveCourseFromCohortsRequest
):
    course_org_id = await get_course_org_id(course_id)
    if course_org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course not found in this organization.")
    
    # Further authorization: ensure cohorts belong to the same organization
    for cohort_id in request.cohort_ids:
        cohort_org_id = await get_cohort_org_id(cohort_id)
        if cohort_org_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="One or more cohorts do not belong to this organization.")

    await remove_course_from_cohorts_from_db(course_id, request.cohort_ids)
    return {"success": True}


@router.get("/{org_id}/{course_id}/cohorts", dependencies=[Depends(role_checker(["ADMIN", "MEMBER", "RECRUITER", "HIRING_MANAGER", "CANDIDATE"]))])
async def get_cohorts_for_course(org_id: int, course_id: int) -> List[CourseCohort]:
    course_org_id = await get_course_org_id(course_id)
    if course_org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course not found in this organization.")
    return await get_cohorts_for_course_from_db(course_id)


@router.get("/{org_id}/{course_id}/tasks", dependencies=[Depends(role_checker(["ADMIN", "MEMBER", "RECRUITER", "HIRING_MANAGER", "CANDIDATE"]))])
async def get_tasks_for_course(org_id: int, course_id: int) -> List[Dict]:
    course_org_id = await get_course_org_id(course_id)
    if course_org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course not found in this organization.")
    return await get_tasks_for_course_from_db(course_id)


@router.put("/{org_id}/{course_id}", dependencies=[Depends(role_checker(["ADMIN"]))])
async def update_course_name(org_id: int, course_id: int, request: UpdateCourseNameRequest):
    course_org_id = await get_course_org_id(course_id)
    if course_org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course not found in this organization.")

    await update_course_name_in_db(course_id, request.name)
    return {"success": True}


@router.put("/{org_id}/{course_id}/milestones/swap", dependencies=[Depends(role_checker(["ADMIN"]))])
async def swap_milestone_ordering(
    org_id: int, course_id: int, request: SwapMilestoneOrderingRequest
):
    course_org_id = await get_course_org_id(course_id)
    if course_org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course not found in this organization.")
    
    milestone_1_org_id = await get_milestone_org_id(request.milestone_1_id)
    milestone_2_org_id = await get_milestone_org_id(request.milestone_2_id)

    if milestone_1_org_id != org_id or milestone_2_org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="One or both milestones not found in this organization.")

    await swap_milestone_ordering_for_course_in_db(
        course_id, request.milestone_1_id, request.milestone_2_id
    )
    return {"success": True}


@router.put("/{org_id}/{course_id}/tasks/swap", dependencies=[Depends(role_checker(["ADMIN"]))])
async def swap_task_ordering(org_id: int, course_id: int, request: SwapTaskOrderingRequest):
    course_org_id = await get_course_org_id(course_id)
    if course_org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course not found in this organization.")
    
    task_1_org_id = await get_task_org_id(request.task_1_id)
    task_2_org_id = await get_task_org_id(request.task_2_id)

    if task_1_org_id != org_id or task_2_org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="One or both tasks not found in this organization.")

    await swap_task_ordering_for_course_in_db(
        course_id, request.task_1_id, request.task_2_id
    )
    return {"success": True}
