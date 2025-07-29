"""
OCR API Routes

Provides endpoints for OCR processing and result management.
"""

import uuid
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.api.deps import CurrentUser, get_db
from app.core.config import settings
from app.models import OCRRecord, OCRRecordCreate, OCRRecordPublic, OCRRecordsPublic, OCRRecordUpdate
from app.ocr_service import ocr_service
from app.r2_storage import r2_storage

logger = logging.getLogger(__name__)

router = APIRouter()


def extract_r2_key_from_url(url: str) -> str | None:
    """Extract R2 file key from URL"""
    try:
        if not url:
            return None
        
        # Handle different URL formats
        if "r2.dev" in url:
            # Format: https://pub-xxx.r2.dev/path/to/file
            return url.split("/", 3)[-1] if "/" in url else None
        elif settings.CLOUDFLARE_R2_PUBLIC_URL and settings.CLOUDFLARE_R2_PUBLIC_URL in url:
            # Custom domain format
            return url.replace(settings.CLOUDFLARE_R2_PUBLIC_URL.rstrip("/") + "/", "")
        else:
            # Assume it's a direct key
            return url
            
    except Exception as e:
        logger.error(f"Failed to extract R2 key from URL {url}: {e}")
        return None


async def cleanup_r2_files(file_keys: list[str]):
    """Clean up files from R2 storage"""
    try:
        for file_key in file_keys:
            success = r2_storage.delete_file(file_key)
            if success:
                logger.info(f"Deleted R2 file: {file_key}")
            else:
                logger.warning(f"Failed to delete R2 file: {file_key}")
    except Exception as e:
        logger.error(f"Error during R2 cleanup: {e}")


@router.post("/process", response_model=OCRRecordPublic)
async def process_ocr(
    *,
    db: Session = Depends(get_db),
    current_user: CurrentUser,
    device_sn: Annotated[str, Form()],
    image_file: UploadFile = File(...),
    language: Annotated[str, Form()] = "ch",
    use_angle_cls: Annotated[bool, Form()] = False,
    use_dilation: Annotated[bool, Form()] = False,
    confidence_thresh: Annotated[float, Form()] = 0.5,
) -> OCRRecord:
    """
    Process OCR on uploaded image file.
    
    Args:
        device_sn: Device serial number
        image_file: Image file to process
        language: OCR language (default: 'ch')
        use_angle_cls: Whether to use document orientation classification
        use_dilation: Whether to use dilation processing
        confidence_thresh: Text recognition confidence threshold (0-1)
    
    Returns:
        OCR processing result
    """
    try:
        # Read file content
        file_content = await image_file.read()
        
        # Validate image
        validation_result = await ocr_service.validate_image(file_content, image_file.filename or "image")
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image file: {validation_result['error']}"
            )
        
        # Create initial OCR record
        ocr_record = OCRRecord(
            device_sn=device_sn,
            original_image_url="",  # Will be updated after file upload
            language=language,
            use_angle_cls=use_angle_cls,
            file_size=validation_result["file_size"],
            image_format=validation_result["format"],
            status="processing",
            created_by=current_user.id,
            scan_time=datetime.utcnow()
        )
        
        db.add(ocr_record)
        db.commit()
        db.refresh(ocr_record)
        
        try:
            # Upload original image to R2 storage
            original_image_url = await ocr_service.upload_to_r2(file_content, image_file.filename or "image")
            
            # Update record with R2 URL
            ocr_record.original_image_url = original_image_url
            db.commit()
            
            # Save to temporary file for OCR processing
            temp_file_path = await ocr_service.save_to_temp_file(file_content, image_file.filename or "image")
            
            # Process OCR
            ocr_result = await ocr_service.process_ocr(
                image_path=temp_file_path,
                language=language,
                use_angle_cls=use_angle_cls,
                confidence_thresh=confidence_thresh
            )
            
            if ocr_result["success"]:
                # Result image is already generated and uploaded in process_ocr method
                # No need to generate again here
                
                # Update OCR record with results
                ocr_record.ocr_text = ocr_result["ocr_text"]
                ocr_record.ocr_confidence = ocr_result["ocr_confidence"]
                ocr_record.detection_boxes = {
                    "boxes": ocr_result["detection_boxes"],
                    "total_boxes": ocr_result["total_boxes"]
                }
                ocr_record.processing_time = ocr_result["processing_time"]
                ocr_record.result_image_url = ocr_result.get("result_image_url", "")
                ocr_record.status = "success"
                
            else:
                # Update record with error
                ocr_record.status = "failed"
                ocr_record.error_message = ocr_result["error"]
                ocr_record.processing_time = ocr_result["processing_time"]
            
            # Clean up temporary file
            await ocr_service.cleanup_temp_files(temp_file_path)
            
            ocr_record.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(ocr_record)
            
            logger.info(f"OCR processing completed for record {ocr_record.id}")
            return ocr_record
            
        except Exception as e:
            # Update record with error status
            ocr_record.status = "failed"
            ocr_record.error_message = str(e)
            ocr_record.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(ocr_record)
            
            logger.error(f"OCR processing failed for record {ocr_record.id}: {e}")
            return ocr_record
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR process endpoint failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during OCR processing"
        )


@router.get("/results", response_model=OCRRecordsPublic)
def get_ocr_results(
    *,
    db: Session = Depends(get_db),
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    device_sn: str | None = None,
) -> OCRRecordsPublic:
    """
    Get OCR results with pagination and optional filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        device_sn: Optional device SN filter
    
    Returns:
        Paginated OCR results
    """
    try:
        # Build query
        query = select(OCRRecord).where(OCRRecord.created_by == current_user.id)
        
        # Add device_sn filter if provided (case-insensitive partial match)
        if device_sn:
            query = query.where(OCRRecord.device_sn.ilike(f"%{device_sn}%"))
        
        # Add ordering and pagination
        query = query.order_by(OCRRecord.scan_time.desc()).offset(skip).limit(limit)
        
        # Execute query
        ocr_records = db.exec(query).all()
        
        # Count total records for pagination
        count_query = select(OCRRecord).where(OCRRecord.created_by == current_user.id)
        if device_sn:
            count_query = count_query.where(OCRRecord.device_sn.ilike(f"%{device_sn}%"))
        
        # Get count
        total_count = len(db.exec(count_query).all())
        
        return OCRRecordsPublic(data=ocr_records, count=total_count)
        
    except Exception as e:
        logger.error(f"Failed to get OCR results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OCR results"
        )


@router.get("/results/{record_id}", response_model=OCRRecordPublic)
def get_ocr_result(
    *,
    db: Session = Depends(get_db),
    current_user: CurrentUser,
    record_id: uuid.UUID,
) -> OCRRecord:
    """
    Get specific OCR result by ID.
    
    Args:
        record_id: OCR record UUID
    
    Returns:
        OCR record details
    """
    try:
        # Query for the specific record
        query = select(OCRRecord).where(
            OCRRecord.id == record_id,
            OCRRecord.created_by == current_user.id
        )
        
        ocr_record = db.exec(query).first()
        
        if not ocr_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OCR record not found"
            )
        
        return ocr_record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get OCR result {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OCR result"
        )


@router.delete("/results/{record_id}")
def delete_ocr_result(
    *,
    db: Session = Depends(get_db),
    current_user: CurrentUser,
    record_id: uuid.UUID,
) -> dict:
    """
    Delete specific OCR result by ID.
    
    Args:
        record_id: OCR record UUID
    
    Returns:
        Success message
    """
    try:
        # Query for the specific record
        query = select(OCRRecord).where(
            OCRRecord.id == record_id,
            OCRRecord.created_by == current_user.id
        )
        
        ocr_record = db.exec(query).first()
        
        if not ocr_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OCR record not found"
            )
        
        # Extract R2 file keys from URLs for deletion
        files_to_delete = []
        if ocr_record.original_image_url:
            # Extract file key from R2 URL
            original_key = extract_r2_key_from_url(ocr_record.original_image_url)
            if original_key:
                files_to_delete.append(original_key)
        if ocr_record.result_image_url:
            # Extract file key from R2 URL  
            result_key = extract_r2_key_from_url(ocr_record.result_image_url)
            if result_key:
                files_to_delete.append(result_key)
        
        # Delete from database
        db.delete(ocr_record)
        db.commit()
        
        # Clean up R2 files asynchronously (don't wait for completion)
        if files_to_delete:
            import asyncio
            asyncio.create_task(cleanup_r2_files(files_to_delete))
        
        logger.info(f"Deleted OCR record {record_id}")
        return {"message": "OCR record deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete OCR result {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete OCR result"
        )


@router.get("/download/{record_id}")
async def download_ocr_text(
    *,
    db: Session = Depends(get_db),
    current_user: CurrentUser,
    record_id: uuid.UUID,
) -> dict:
    """
    Download OCR result as text file.
    
    Args:
        record_id: OCR record UUID
    
    Returns:
        Download information
    """
    try:
        # Query for the specific record
        query = select(OCRRecord).where(
            OCRRecord.id == record_id,
            OCRRecord.created_by == current_user.id
        )
        
        ocr_record = db.exec(query).first()
        
        if not ocr_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OCR record not found"
            )
        
        if not ocr_record.ocr_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No OCR text available for download"
            )
        
        # Format download content
        download_content = f"""OCR Result
Device SN: {ocr_record.device_sn}
Scan Time: {ocr_record.scan_time}
Language: {ocr_record.language}
Confidence: {ocr_record.ocr_confidence:.2f}
Processing Time: {ocr_record.processing_time:.2f}s

Recognized Text:
{ocr_record.ocr_text}
"""
        
        # In a real implementation, this would create a downloadable file
        # For now, return the content
        return {
            "content": download_content,
            "filename": f"ocr_result_{ocr_record.device_sn}_{ocr_record.scan_time.strftime('%Y%m%d_%H%M%S')}.txt",
            "content_type": "text/plain"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download OCR result {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download OCR result"
        ) 