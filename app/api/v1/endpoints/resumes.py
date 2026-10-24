"""Resume and document management endpoints."""
from typing import List
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.profile.schemas import ResumeResponse
from app.profile.service import ProfileService

router = APIRouter(prefix="/resumes", tags=["Resumes & Documents"])


@router.post("/upload", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED, summary="Upload a new resume")
async def upload_resume(
    file: UploadFile = File(...),
    is_primary: bool = Form(default=False),
    db: AsyncSession = Depends(get_db),
):
    service = ProfileService(db)
    try:
        content = await file.read()
        doc = await service.save_resume_file(
            raw_filename=file.filename or "resume.pdf",
            content=content,
            is_primary=is_primary,
        )
        return ResumeResponse(
            id=doc.id,
            filename=doc.filename,
            file_size_bytes=doc.file_size_bytes,
            file_type=doc.file_type,
            extracted_text_preview=(doc.extracted_text or "")[:300],
            is_primary=doc.is_primary,
            created_at=doc.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[ResumeResponse], summary="List stored resumes")
async def list_resumes(db: AsyncSession = Depends(get_db)):
    service = ProfileService(db)
    docs = await service.get_resumes()
    return [
        ResumeResponse(
            id=d.id,
            filename=d.filename,
            file_size_bytes=d.file_size_bytes,
            file_type=d.file_type,
            extracted_text_preview=(d.extracted_text or "")[:300],
            is_primary=d.is_primary,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a resume document")
async def delete_resume(resume_id: int, db: AsyncSession = Depends(get_db)):
    service = ProfileService(db)
    deleted = await service.delete_resume(resume_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
