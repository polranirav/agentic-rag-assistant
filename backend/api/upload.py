"""
Document Upload API: Handle file uploads and trigger ingestion
"""

import os
import shutil
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload", tags=["upload"])

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".csv", ".json"}

# Get data directory
def get_data_dir() -> Path:
    """Get the data/raw directory path."""
    script_dir = Path(__file__).parent.parent
    project_root = script_dir.parent.parent
    return project_root / "data" / "raw"


class UploadResponse(BaseModel):
    """Response model for file upload."""
    success: bool
    message: str
    filename: str
    file_type: str
    file_size: int
    documents_count: Optional[int] = None


class DocumentInfo(BaseModel):
    """Document information model."""
    filename: str
    file_type: str
    file_size: int
    uploaded_at: str


@router.get("/documents", response_model=List[DocumentInfo])
async def list_documents():
    """List all uploaded documents."""
    data_dir = get_data_dir()
    documents = []
    
    if not data_dir.exists():
        return documents
    
    # Scan all subdirectories
    for file_type_dir in data_dir.iterdir():
        if file_type_dir.is_dir():
            for file_path in file_type_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
                    stat = file_path.stat()
                    documents.append(DocumentInfo(
                        filename=file_path.name,
                        file_type=file_path.suffix.lower().replace(".", "").upper(),
                        file_size=stat.st_size,
                        uploaded_at=datetime.fromtimestamp(stat.st_mtime).isoformat()
                    ))
    
    return sorted(documents, key=lambda x: x.uploaded_at, reverse=True)


@router.post("/", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document (PDF, TXT, MD, DOCX, CSV, JSON).
    
    The file will be saved to data/raw/{file_type}/ and can be ingested later.
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Get data directory
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create type-specific directory (e.g., PDF/, TXT/, MD/)
    file_type = file_ext.replace(".", "").upper()
    type_dir = data_dir / file_type
    type_dir.mkdir(exist_ok=True)
    
    # Save file
    file_path = type_dir / file.filename
    
    try:
        # Check if file already exists
        if file_path.exists():
            # Add timestamp to filename
            stem = file_path.stem
            timestamp = int(time.time())
            file_path = type_dir / f"{stem}_{timestamp}{file_ext}"
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = file_path.stat().st_size
        
        logger.info(f"✅ Uploaded: {file.filename} ({file_size} bytes) to {file_path}")
        
        return UploadResponse(
            success=True,
            message=f"File uploaded successfully. Ready for ingestion.",
            filename=file.filename,
            file_type=file_type,
            file_size=file_size
        )
    
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.delete("/documents/{filename:path}")
async def delete_document(filename: str):
    """Delete a document by filename."""
    from urllib.parse import unquote
    
    # Decode URL-encoded filename
    decoded_filename = unquote(filename)
    data_dir = get_data_dir()
    
    logger.info(f"🗑️ Delete request for: {decoded_filename}")
    
    # Search for file in all type directories
    for file_type_dir in data_dir.iterdir():
        if file_type_dir.is_dir():
            file_path = file_type_dir / decoded_filename
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.info(f"✅ Deleted: {decoded_filename} from {file_type_dir}")
                    return {"success": True, "message": f"Deleted {decoded_filename}"}
                except Exception as e:
                    logger.error(f"❌ Delete failed for {decoded_filename}: {e}")
                    raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
    
    logger.warning(f"⚠️ File not found: {decoded_filename}")
    raise HTTPException(status_code=404, detail=f"File not found: {decoded_filename}")


@router.post("/ingest")
async def trigger_ingestion():
    """
    Trigger document ingestion pipeline.
    
    This will process all documents in data/raw/ and upload them to Pinecone.
    """
    try:
        # Import here to avoid circular imports
        import subprocess
        import sys
        
        script_path = Path(__file__).parent.parent / "scripts" / "ingest.py"
        
        if not script_path.exists():
            raise HTTPException(status_code=500, detail="Ingestion script not found")
        
        # Run ingestion script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=script_path.parent.parent
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Ingestion failed: {result.stderr}"
            )
        
        return {
            "success": True,
            "message": "Ingestion completed successfully",
            "output": result.stdout
        }
    
    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
