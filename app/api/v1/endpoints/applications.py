"""Application lifecycle, browser automation, and approval endpoints."""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation.browser import BrowserAutomationService
from app.automation.schemas import BrowserActionRequest, BrowserActionResponse
from app.db.models import Application, JobListing
from app.db.session import get_db

router = APIRouter(prefix="/applications", tags=["Application Automation & Approvals"])


@router.post("/prepare", response_model=BrowserActionResponse, summary="Inspect form and pre-fill fields in dry-run mode")
async def prepare_application(
    req: BrowserActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Executes safe dry-run form filling and stops before submission, awaiting human approval."""
    # Force dry-run = True for prepare endpoint
    req.dry_run = True
    req.user_confirmed_submission = False

    service = BrowserAutomationService(db)
    try:
        return await service.execute_application_flow(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Browser automation error: {str(e)}")


@router.post("/submit", response_model=BrowserActionResponse, summary="Submit application with explicit user approval")
async def submit_application(
    req: BrowserActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submits the application only when user_confirmed_submission is explicitly True."""
    if not req.user_confirmed_submission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Safety Violation: user_confirmed_submission must be True to authorize final submission."
        )

    req.dry_run = False
    service = BrowserAutomationService(db)
    try:
        return await service.execute_application_flow(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Submission error: {str(e)}")


@router.post("/{app_id}/approve-and-submit", response_model=BrowserActionResponse, summary="Approve and submit a previously pre-filled application")
async def approve_and_submit_application(
    app_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Explicit human approval endpoint to submit an application previously held in READY_FOR_APPROVAL."""
    stmt = select(Application).where(Application.id == app_id)
    app_record = (await db.execute(stmt)).scalar_one_or_none()
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Application ID {app_id} not found")

    req = BrowserActionRequest(
        job_id=app_record.job_id,
        resume_id=app_record.resume_id,
        draft_id=app_record.draft_id,
        user_confirmed_submission=True,
        dry_run=False,
    )
    service = BrowserAutomationService(db)
    try:
        return await service.execute_application_flow(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Approval submission error: {str(e)}")


@router.get("", summary="List application records and tracking statuses")
async def list_applications(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    query = select(Application, JobListing).join(JobListing, Application.job_id == JobListing.id).order_by(Application.created_at.desc())
    results = (await db.execute(query)).all()

    output = []
    for app, job in results:
        output.append({
            "id": app.id,
            "job_id": app.job_id,
            "job_title": job.title,
            "company": job.company,
            "location": job.location,
            "source": job.source,
            "application_url": job.application_url,
            "status": app.status,
            "requires_approval": app.requires_approval,
            "is_user_approved": app.is_user_approved,
            "last_step": app.last_step,
            "confirmation_reference": app.confirmation_reference,
            "error_message": app.error_message,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
        })
    return output


@router.delete("/{app_id}", summary="Delete or dismiss an application record")
async def delete_application(app_id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Delete or dismiss a tracked application record."""
    stmt = select(Application).where(Application.id == app_id)
    app_record = (await db.execute(stmt)).scalar_one_or_none()
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    await db.delete(app_record)
    await db.commit()
    return {"success": True, "message": f"Application {app_id} deleted successfully"}


@router.get("/{app_id}", summary="Get application details and audit log")
async def get_application(app_id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    query = select(Application, JobListing).join(JobListing, Application.job_id == JobListing.id).where(Application.id == app_id)
    row = (await db.execute(query)).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    app, job = row
    return {
        "id": app.id,
        "job_id": app.job_id,
        "job_title": job.title,
        "company": job.company,
        "application_url": job.application_url,
        "status": app.status,
        "requires_approval": app.requires_approval,
        "is_user_approved": app.is_user_approved,
        "last_step": app.last_step,
        "confirmation_reference": app.confirmation_reference,
        "error_message": app.error_message,
        "audit_notes": app.audit_notes,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "approved_at": app.approved_at.isoformat() if app.approved_at else None,
        "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
    }
