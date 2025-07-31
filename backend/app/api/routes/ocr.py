"""
OCR API Routes

Provides endpoints for OCR processing and result management.
"""

import uuid
import logging
from datetime import datetime, date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Body
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
    waybill_number: str | None = None,
    carrier: str | None = None,
    recipient: str | None = None,
    audit_status: str | None = None,
    upload_date_start: str | None = None,
    upload_date_end: str | None = None,
    shipping_date_start: str | None = None,
    shipping_date_end: str | None = None,
    delivery_date_start: str | None = None,
    delivery_date_end: str | None = None,
) -> OCRRecordsPublic:
    """
    Get OCR results with pagination and filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        device_sn: Optional device SN filter
        waybill_number: Optional waybill number filter
        carrier: Optional carrier filter
        recipient: Optional recipient filter
        audit_status: Optional audit status filter
        upload_date_start: Optional upload date start filter (YYYY-MM-DD)
        upload_date_end: Optional upload date end filter (YYYY-MM-DD)
        shipping_date_start: Optional shipping date start filter (YYYY-MM-DD)
        shipping_date_end: Optional shipping date end filter (YYYY-MM-DD)
        delivery_date_start: Optional delivery date start filter (YYYY-MM-DD)  
        delivery_date_end: Optional delivery date end filter (YYYY-MM-DD)
    
    Returns:
        Paginated OCR results
    """
    try:
        # Build base query
        query = select(OCRRecord).where(OCRRecord.created_by == current_user.id)
        
        # Add device_sn filter if provided (case-insensitive partial match)
        if device_sn:
            query = query.where(OCRRecord.device_sn.ilike(f"%{device_sn}%"))
        
        # Add waybill_number filter if provided (case-insensitive partial match)
        if waybill_number:
            query = query.where(OCRRecord.waybill_number.ilike(f"%{waybill_number}%"))
        
        # Add carrier filter if provided (case-insensitive partial match)
        if carrier:
            query = query.where(OCRRecord.carrier.ilike(f"%{carrier}%"))
        
        # Add recipient filter if provided (case-insensitive partial match)  
        if recipient:
            query = query.where(OCRRecord.recipient.ilike(f"%{recipient}%"))
        
        # Add audit status filter if provided (exact match, ignore "全部")
        if audit_status and audit_status != "全部":
            query = query.where(OCRRecord.audit_status == audit_status)
        
        # Add date range filters
        if upload_date_start:
            try:
                start_date = date.fromisoformat(upload_date_start)
                query = query.where(OCRRecord.upload_date >= start_date)
            except ValueError:
                pass  # 无效的日期格式，忽略过滤条件
        
        if upload_date_end:
            try:
                end_date = date.fromisoformat(upload_date_end)
                query = query.where(OCRRecord.upload_date <= end_date)
            except ValueError:
                pass  # 无效的日期格式，忽略过滤条件
        
        if shipping_date_start:
            try:
                start_date = date.fromisoformat(shipping_date_start)
                query = query.where(OCRRecord.shipping_date >= start_date)
            except ValueError:
                pass  # 无效的日期格式，忽略过滤条件
        
        if shipping_date_end:
            try:
                end_date = date.fromisoformat(shipping_date_end)
                query = query.where(OCRRecord.shipping_date <= end_date)
            except ValueError:
                pass  # 无效的日期格式，忽略过滤条件
        
        if delivery_date_start:
            try:
                start_date = date.fromisoformat(delivery_date_start)
                query = query.where(OCRRecord.delivery_date >= start_date)
            except ValueError:
                pass  # 无效的日期格式，忽略过滤条件
        
        if delivery_date_end:
            try:
                end_date = date.fromisoformat(delivery_date_end)
                query = query.where(OCRRecord.delivery_date <= end_date)
            except ValueError:
                pass  # 无效的日期格式，忽略过滤条件
        
        # Get total count for pagination (before applying limit/offset)
        count_query = query
        total_count = len(db.exec(count_query).all())
        
        # Add ordering and pagination
        query = query.order_by(OCRRecord.scan_time.desc()).offset(skip).limit(limit)
        
        # Execute query
        ocr_records = db.exec(query).all()
        
        logger.info(f"Found {len(ocr_records)} OCR records (total: {total_count}) for user {current_user.id}")
        
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


@router.put("/results/{record_id}", response_model=OCRRecordPublic)
def update_ocr_result(
    *,
    db: Session = Depends(get_db),
    current_user: CurrentUser,
    record_id: uuid.UUID,
    record_update: OCRRecordUpdate,
) -> OCRRecord:
    """
    Update specific OCR result by ID.
    
    Args:
        record_id: OCR record UUID
        record_update: Updated record data
    
    Returns:
        Updated OCR record
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
        
        # Update fields from the request
        update_data = record_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(ocr_record, field):
                setattr(ocr_record, field, value)
        
        # Update timestamp
        ocr_record.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(ocr_record)
        
        logger.info(f"Updated OCR record {record_id}")
        return ocr_record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update OCR result {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update OCR result"
        )


@router.put("/results/{record_id}/waybill")
def update_waybill_info(
    *,
    db: Session = Depends(get_db),
    current_user: CurrentUser,
    record_id: uuid.UUID,
    waybill_data: dict = Body(...),
) -> OCRRecordPublic:
    """
    Update waybill information for specific OCR record.
    
    Args:
        record_id: OCR record UUID
        waybill_number: Waybill number
        carrier: Carrier/logistics company
        shipping_date: Shipping date (YYYY-MM-DD)
        recipient: Recipient name
        delivery_date: Delivery date (YYYY-MM-DD) 
        upload_date: Upload date (YYYY-MM-DD)
        uploader: Uploader name
    
    Returns:
        Updated OCR record
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
        
        # Update waybill fields
        waybill_number = waybill_data.get('waybill_number')
        if waybill_number is not None:
            ocr_record.waybill_number = waybill_number
        
        carrier = waybill_data.get('carrier')
        if carrier is not None:
            ocr_record.carrier = carrier
        
        shipping_date = waybill_data.get('shipping_date')
        if shipping_date is not None:
            try:
                # 只支持日期格式: YYYY-MM-DD
                if shipping_date and isinstance(shipping_date, str):
                    if 'T' in shipping_date:
                        # 如果包含时间部分，只取日期部分
                        shipping_date = shipping_date.split('T')[0]
                    # 转换为日期对象
                    ocr_record.shipping_date = date.fromisoformat(shipping_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="无效的发货日期格式。请使用 YYYY-MM-DD 格式"
                )
        
        recipient = waybill_data.get('recipient')
        if recipient is not None:
            ocr_record.recipient = recipient
        
        delivery_date = waybill_data.get('delivery_date')
        if delivery_date is not None:
            try:
                # 只支持日期格式: YYYY-MM-DD
                if delivery_date and isinstance(delivery_date, str):
                    if 'T' in delivery_date:
                        # 如果包含时间部分，只取日期部分
                        delivery_date = delivery_date.split('T')[0]
                    # 转换为日期对象
                    ocr_record.delivery_date = date.fromisoformat(delivery_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="无效的签收日期格式。请使用 YYYY-MM-DD 格式"
                )
        
        upload_date = waybill_data.get('upload_date')
        if upload_date is not None:
            try:
                # 只支持日期格式: YYYY-MM-DD
                if upload_date and isinstance(upload_date, str):
                    if 'T' in upload_date:
                        # 如果包含时间部分，只取日期部分
                        upload_date = upload_date.split('T')[0]
                    # 转换为日期对象
                    ocr_record.upload_date = date.fromisoformat(upload_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="无效的上传日期格式。请使用 YYYY-MM-DD 格式"
                )
        
        uploader = waybill_data.get('uploader')
        if uploader is not None:
            ocr_record.uploader = uploader
        
        # Update timestamp
        ocr_record.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(ocr_record)
        
        logger.info(f"Updated waybill info for OCR record {record_id}")
        return ocr_record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update waybill info for OCR result {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update waybill information"
        )


@router.put("/results/{record_id}/audit")  
def update_audit_status(
    *,
    db: Session = Depends(get_db),
    current_user: CurrentUser,
    record_id: uuid.UUID,
    audit_data: dict = Body(...),
) -> OCRRecordPublic:
    """
    Update audit status for specific OCR record.
    
    Args:
        record_id: OCR record UUID
        audit_status: New audit status (未审核/已审核/审核通过/审核不通过)
    
    Returns:
        Updated OCR record
    """
    try:
        # Get audit status from request body
        audit_status = audit_data.get('audit_status')
        if not audit_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="audit_status is required"
            )
        
        # Validate audit status
        valid_statuses = ["未审核", "已审核", "审核通过", "审核不通过"]
        if audit_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid audit status. Must be one of: {', '.join(valid_statuses)}"
            )
        
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
        
        # Update audit status
        ocr_record.audit_status = audit_status
        ocr_record.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(ocr_record)
        
        logger.info(f"Updated audit status to '{audit_status}' for OCR record {record_id}")
        return ocr_record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update audit status for OCR result {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update audit status"
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


def extract_waybill_info(ocr_text: str) -> dict:
    """
    从OCR识别文本中提取面单信息
    
    这是一个简单的信息提取函数，可以根据实际需求进行优化
    """
    import re
    
    extracted = {}
    
    if not ocr_text:
        return extracted
    
    # 提取运单号（通常是数字组合）
    waybill_patterns = [
        r'(\d{10,20})',  # 10-20位数字
        r'([A-Z]{2,4}\d{8,15})',  # 字母+数字组合
    ]
    
    for pattern in waybill_patterns:
        match = re.search(pattern, ocr_text)
        if match:
            extracted["waybill_number"] = match.group(1)
            break
    
    # 提取常见快递公司名称
    carriers = [
        "顺丰", "圆通", "申通", "中通", "韵达", "百世", "德邦", "京东", "菜鸟",
        "EMS", "邮政", "天天", "宅急送", "国通", "全峰", "速尔", "优速"
    ]
    
    for carrier in carriers:
        if carrier in ocr_text:
            extracted["carrier"] = carrier
            break
    
    # 提取收件人信息（简单匹配）
    recipient_patterns = [
        r'收件人[：:]\s*([^\s\n]{2,10})',
        r'签收人[：:]\s*([^\s\n]{2,10})',
    ]
    
    for pattern in recipient_patterns:
        match = re.search(pattern, ocr_text)
        if match:
            extracted["recipient"] = match.group(1)
            break
    
    # 提取日期信息
    date_patterns = [
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'(\d{4}年\d{1,2}月\d{1,2}日)',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, ocr_text)
        if match:
            date_str = match.group(1)
            # 标准化日期格式
            date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
            date_str = date_str.replace('/', '-')
            extracted["shipping_date"] = date_str
            break
    
    return extracted


@router.post("/upload-waybill", response_model=OCRRecordPublic)
async def upload_waybill(
    *,
    db: Session = Depends(get_db),
    current_user: CurrentUser,
    image_file: UploadFile = File(...),
    device_sn: Annotated[str | None, Form()] = None,
) -> OCRRecord:
    """
    上传面单图片并进行OCR识别
    
    这是专门为面单管理新增按钮设计的接口，
    会自动生成设备序列号并进行OCR处理。
    
    Args:
        image_file: 面单图片文件
        device_sn: 可选的设备序列号，如果不提供会自动生成
    
    Returns:
        OCR识别结果
    """
    try:
        # 如果没有提供设备序列号，自动生成一个
        if not device_sn:
            device_sn = f"WAYBILL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(current_user.id)[:8]}"
        
        # 读取文件内容
        file_content = await image_file.read()
        
        # 验证图片文件
        validation_result = await ocr_service.validate_image(
            file_content, 
            image_file.filename or "waybill_image"
        )
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的图片文件: {validation_result['error']}"
            )
        
        # 创建OCR记录
        ocr_record = OCRRecord(
            device_sn=device_sn,
            original_image_url="",  # 将在文件上传后更新
            language="ch",  # 默认中文识别
            use_angle_cls=True,  # 启用文档方向分类
            file_size=validation_result["file_size"],
            image_format=validation_result["format"],
            status="processing",
            created_by=current_user.id,
            scan_time=datetime.utcnow(),
            upload_date=date.today(),  # 设置上传日期为今天
            uploader=current_user.full_name or current_user.email,  # 设置上传人
            audit_status="未审核"  # 默认审核状态
        )
        
        db.add(ocr_record)
        db.commit()
        db.refresh(ocr_record)
        
        try:
            # 上传原始图片到R2存储
            original_image_url = await ocr_service.upload_to_r2(
                file_content, 
                image_file.filename or "waybill_image"
            )
            
            # 更新记录中的图片URL
            ocr_record.original_image_url = original_image_url
            db.commit()
            
            # 保存到临时文件进行OCR处理
            temp_file_path = await ocr_service.save_to_temp_file(
                file_content, 
                image_file.filename or "waybill_image"
            )
            
            # 执行OCR识别
            ocr_result = await ocr_service.process_ocr(
                image_path=temp_file_path,
                language="ch",
                use_angle_cls=True,
                confidence_thresh=0.6,  # 面单识别使用较高的置信度阈值
                ocr_record_id=str(ocr_record.id)
            )
            
            if ocr_result["success"]:
                # 更新OCR记录
                ocr_record.ocr_text = ocr_result["ocr_text"]
                ocr_record.ocr_confidence = ocr_result["ocr_confidence"]
                ocr_record.detection_boxes = {
                    "boxes": ocr_result["detection_boxes"],
                    "total_boxes": ocr_result["total_boxes"]
                }
                ocr_record.processing_time = ocr_result["processing_time"]
                ocr_record.result_image_url = ocr_result.get("result_image_url", "")
                ocr_record.status = "success"
                
                # 尝试从OCR文本中提取面单信息
                extracted_info = extract_waybill_info(ocr_result["ocr_text"])
                if extracted_info:
                    ocr_record.waybill_number = extracted_info.get("waybill_number")
                    ocr_record.carrier = extracted_info.get("carrier")
                    ocr_record.recipient = extracted_info.get("recipient")
                    if extracted_info.get("shipping_date"):
                        try:
                            ocr_record.shipping_date = date.fromisoformat(
                                extracted_info["shipping_date"]
                            )
                        except ValueError:
                            pass
                
            else:
                # 处理失败
                ocr_record.status = "failed"
                ocr_record.error_message = ocr_result["error"]
                ocr_record.processing_time = ocr_result["processing_time"]
            
            # 清理临时文件
            await ocr_service.cleanup_temp_files(temp_file_path)
            
            ocr_record.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(ocr_record)
            
            logger.info(f"面单上传和OCR处理完成，记录ID: {ocr_record.id}")
            return ocr_record
            
        except Exception as e:
            # 更新记录状态为失败
            ocr_record.status = "failed"
            ocr_record.error_message = str(e)
            ocr_record.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(ocr_record)
            
            logger.error(f"面单OCR处理失败，记录ID: {ocr_record.id}, 错误: {e}")
            return ocr_record
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"面单上传接口失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="面单上传处理失败"
        )
