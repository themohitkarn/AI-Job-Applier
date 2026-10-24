"""Application content generation and draft review endpoints."""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.generation.schemas import ApproveDraftRequest, GenerateContentRequest, GeneratedContentResponse
from app.generation.service import ContentService

router = APIRouter(prefix="/content", tags=["Content Generation & Drafts"])


@router.post("/generate", response_model=GeneratedContentResponse, summary="Generate tailored application materials")
async def generate_application_content(req: GenerateContentRequest, db: AsyncSession = Depends(get_db)):
    service = ContentService(db)
    try:
        response = await service.generate_content(req)
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Generation failed: {str(e)}")


@router.put("/drafts/{draft_id}/approve", summary="Approve and finalize application draft")
async def approve_draft(
    draft_id: int,
    req: ApproveDraftRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ContentService(db)
    try:
        draft = await service.approve_draft(draft_id, req)
        return {
            "id": draft.id,
            "job_id": draft.job_id,
            "draft_type": draft.draft_type,
            "subject": draft.subject,
            "content": draft.content,
            "is_approved": draft.is_approved,
            "file_path": draft.file_path,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
