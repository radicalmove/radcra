"""Admin-only per-course enrollment and reviewed role transfers."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db import get_session
from app.dependencies import current_dashboard_user
from app.models import Course, User
from app.routers.auth import _form_with_csrf, _csrf_response
from app.services.access import AccessDenied
from app.services.course_onboarding import require_admin, set_enrollment
from app.services.course_migration import preview_transfer, apply_transfer

router=APIRouter(prefix="/admin")


def _admin(user):
    try:
        require_admin(user)
    except AccessDenied as exc:
        raise HTTPException(403,detail="Administrator access required") from exc


def _page(request, **context):
    # Shared auth helper supplies the existing double-submit CSRF cookie.
    return _csrf_response(request,"admin/course_migration.html",context)


@router.post("/courses/{course_id}/email-onboarding")
async def enrollment(course_id:uuid.UUID,request:Request,user:User=Depends(current_dashboard_user),
                     db:Session=Depends(get_session)):
    _admin(user)
    form=await _form_with_csrf(request)
    if form.get("enabled") not in {"true","false"}:
        raise HTTPException(422,detail="Choose enabled or disabled")
    course=db.get(Course,course_id)
    try:
        set_enrollment(db,user,course,form["enabled"]=="true")
    except AccessDenied as exc:
        raise HTTPException(422,detail=str(exc)) from exc
    return RedirectResponse(f"/admin/users?course_id={course_id}",status_code=303)


@router.get("/course-migration")
def index(request:Request,user:User=Depends(current_dashboard_user)):
    _admin(user)
    return _page(request)


@router.post("/course-migration/preview")
async def preview(request:Request,user:User=Depends(current_dashboard_user),db:Session=Depends(get_session)):
    _admin(user)
    form=await _form_with_csrf(request)
    try:
        result=preview_transfer(db,user,str(form.get("source_url","")),str(form.get("target_url","")))
    except AccessDenied as exc:
        raise HTTPException(422,detail=str(exc)) from exc
    return _page(request,preview=result,source=db.get(Course,result.source_course_id),
                 target=db.get(Course,result.target_course_id))


@router.post("/course-migration/{preview_id}/apply")
async def apply(preview_id:uuid.UUID,request:Request,user:User=Depends(current_dashboard_user),db:Session=Depends(get_session)):
    _admin(user)
    form=await _form_with_csrf(request)
    if form.get("confirm")!="yes":
        raise HTTPException(422,detail="Confirm the selected transfers")
    try:
        result=apply_transfer(db,user,preview_id,(await request.form()).getlist("membership_id"))
    except AccessDenied as exc:
        db.rollback()
        raise HTTPException(409,detail=str(exc)) from exc
    return _page(request,completed=len(result))
