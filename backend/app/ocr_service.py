"""
OCR Service Module

This module provides OCR processing functionality using PaddleOCR.
Integrated with Cloudflare R2 storage for image management.
"""

import uuid
import asyncio
import json
import logging
import tempfile
import os
from datetime import datetime
from typing import Any, Dict, List
from pathlib import Path
from io import BytesIO
import aiofiles
import cv2
import numpy as np
from PIL import Image

from app.core.config import settings
from app.r2_storage import r2_storage

logger = logging.getLogger(__name__)

# Add detailed logging for OCR operations
logger.info("🔧 Initializing OCR Service Module")
"""
OCR Service Module

This module provides OCR processing functionality using PaddleOCR.
Integrated with Cloudflare R2 storage for image management.
"""



class OCREngine:
    """PaddleOCR Engine wrapper"""
    
    def __init__(self, use_textline_orientation: bool = False, lang: str = "ch", use_gpu: bool = False):
        self.use_textline_orientation = use_textline_orientation
        self.lang = lang
        self.use_gpu = use_gpu
        self.ocr = None
        self._initialize_ocr()
    
    def _initialize_ocr(self):
        """Initialize PaddleOCR engine"""
        try:
            logger.info("🚀 Initializing PaddleOCR engine...")
            
            # 应用PaddlePaddle兼容性修复
            try:
                import paddle
                if hasattr(paddle, 'base') and hasattr(paddle.base, 'libpaddle'):
                    if hasattr(paddle.base.libpaddle, 'AnalysisConfig'):
                        if not hasattr(paddle.base.libpaddle.AnalysisConfig, 'set_optimization_level'):
                            paddle.base.libpaddle.AnalysisConfig.set_optimization_level = lambda self, level: None
                            logger.info("✅ Applied PaddlePaddle compatibility fix for set_optimization_level")
                
                # 修复其他可能的兼容性问题
                if hasattr(paddle, 'fluid') and not hasattr(paddle.fluid, 'layers'):
                    import paddle.nn as layers
                    paddle.fluid.layers = layers
                    logger.info("✅ Applied PaddlePaddle compatibility fix for fluid.layers")
                    
            except Exception as fix_error:
                logger.warning(f"⚠️ PaddlePaddle compatibility fix failed: {fix_error}")
            
            from paddleocr import PaddleOCR
            
            # Check if PaddleOCR is properly installed
            logger.info(f"📋 OCR Configuration: lang={self.lang}, use_textline_orientation={self.use_textline_orientation}, use_gpu={self.use_gpu}")
            
            # 初始化PaddleOCR引擎
            # 初始化PaddleOCR引擎 (适配PaddleOCR 3.1.0+ API)
            self.ocr = PaddleOCR(
                use_textline_orientation=self.use_textline_orientation,  # 文本行方向分类
                lang=self.lang,  # 语言
                use_gpu=self.use_gpu and self._has_gpu()  # GPU设备
            )
            
            # 初始化结果路径
            self.result_image_path = ""
            self.result_json_path = ""
            self.temp_dir = ""
            
            logger.info(f"✅ PaddleOCR引擎初始化成功: lang={self.lang}, use_textline_orientation={self.use_textline_orientation}, device={'gpu' if self.use_gpu else 'cpu'}")
            
            # 测试OCR引擎初始化
            logger.info("🧪 测试PaddleOCR引擎初始化...")
            
        except ImportError as e:
            logger.error(f"❌ PaddleOCR not available - ImportError: {e}")
            logger.warning("⚠️  Falling back to Mock OCR Engine for development")
            logger.info("💡 To fix this, install PaddleOCR: pip install paddlepaddle paddleocr")
            self._initialize_mock_ocr()
        except Exception as e:
            logger.error(f"❌ Failed to initialize PaddleOCR: {e}")
            logger.warning("⚠️  Falling back to Mock OCR Engine")
            self._initialize_mock_ocr()
    
    def _has_gpu(self) -> bool:
        """Check if GPU is available"""
        try:
            import paddle
            return paddle.device.get_device() != 'cpu'
        except:
            return False
    
    def _initialize_mock_ocr(self):
        """Initialize mock OCR for fallback"""
        self.ocr = None
        logger.info("Using Mock OCR Engine")
    
    def predict(self, image_path: str) -> List[Dict[str, Any]]:
        """OCR prediction with 30 second timeout"""
        try:
            logger.info(f"🔍 Starting OCR prediction for image: {image_path}")
            
            if self.ocr is None:
                logger.warning("⚠️  Using Mock OCR - PaddleOCR not available")
                return self._mock_predict(image_path)
            
            # Verify image file exists and is readable
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            logger.info(f"📁 Image file exists: {image_path} (size: {os.path.getsize(image_path)} bytes)")
            
            # Use real PaddleOCR with timeout
            logger.info("🤖 Running PaddleOCR prediction with 30s timeout...")
            
            import signal
            import threading
            
            result = None
            exception = None
            
            def ocr_worker():
                nonlocal result, exception
                try:
                    result = self.ocr.predict(image_path)
                except Exception as e:
                    exception = e
            
            # Start OCR in a separate thread
            thread = threading.Thread(target=ocr_worker)
            thread.daemon = True
            thread.start()
            
            # Wait for completion with timeout
            thread.join(timeout=30.0)
            
            if thread.is_alive():
                # Timeout occurred
                logger.error("❌ OCR prediction timeout after 30 seconds")
                raise TimeoutError("OCR识别调用超时")
            
            if exception:
                raise exception
            
            if result is None:
                raise RuntimeError("OCR prediction returned no result")
            
            logger.info(f"📊 Raw OCR result type: {type(result)}, length: {len(result) if result else 0}")
            logger.debug(f"📋 Raw OCR result: {result}")

            # 创建临时目录用于保存结果图片
            temp_dir = tempfile.mkdtemp(prefix="ocr_result_")
            self.temp_dir = temp_dir
            self.result_image_path = ""
            self.result_json_path = "" # 不再使用JSON文件

            formatted_results = []
            
            # 统一处理新旧版本的PaddleOCR结果
            if result:
                # PaddleOCR 3.0+ 返回一个包含 Result 对象的列表
                # 旧版本返回一个包含列表的列表
                if isinstance(result, list) and len(result) > 0:
                    # 检查是否是新版Result对象
                    if hasattr(result[0], 'get_text_lines'):
                        logger.info("📋 Processing new PaddleOCR result format (Result object)")
                        try:
                            # 保存可视化结果图片
                            img_path = os.path.join(temp_dir, "result_image.jpg")
                            result[0].save_to_img(img_path)
                            self.result_image_path = img_path
                            logger.info(f"✅ Saved OCR result image to: {img_path}")
                        except Exception as e:
                            logger.warning(f"⚠️ Could not save result image using new API: {e}")

                        text_lines = result[0].get_text_lines()
                        for line in text_lines:
                            formatted_results.append({
                                "text": line.text,
                                "confidence": line.score,
                                "box": line.box.tolist()
                            })
                            logger.info(f"✅ Extracted text: '{line.text}' (Confidence: {line.score:.3f})")
                    
                    # 处理旧版格式或类似结构的返回
                    elif isinstance(result[0], list):
                        logger.info("📋 Processing old PaddleOCR result format (list of lists)")
                        # result[0] 包含所有文本行
                        for line in result[0]:
                            if line and len(line) >= 2:
                                box = line[0]
                                text_info = line[1]
                                if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                                    text, confidence = text_info
                                    formatted_results.append({
                                        "text": text,
                                        "confidence": float(confidence),
                                        "box": box
                                    })
                                    logger.info(f"✅ Extracted text: '{text}' (Confidence: {confidence:.3f})")

            if not formatted_results:
                 logger.warning("⚠️ No text detected in the image or result format not recognized.")

            logger.info(f"🎯 OCR finished: Extracted {len(formatted_results)} text regions")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ OCR prediction failed: {e}")
            logger.exception("Full error traceback:")
            # Fall back to mock OCR on error
            logger.info("🔄 Falling back to Mock OCR")
            return self._mock_predict(image_path)
    
    def _mock_predict(self, image_path: str) -> List[Dict[str, Any]]:
        """Mock OCR prediction for fallback"""
        try:
            logger.warning("🎭 Using Mock OCR - This is for development only!")
            logger.info(f"📁 Mock processing image: {image_path}")
            
            # Simulate OCR processing time
            import time
            time.sleep(0.5)
            
            # Try to get some basic image info for more realistic mock
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    width, height = img.size
                    logger.info(f"📐 Image dimensions: {width}x{height}")
            except Exception:
                width, height = 800, 600
            
            # Mock OCR result with more realistic data
            mock_result = [
                {
                    "text": "这是一个模拟的OCR识别结果",
                    "confidence": 0.95,
                    "box": [[50, 50], [min(400, width-50), 50], [min(400, width-50), 80], [50, 80]]
                },
                {
                    "text": "Mock OCR Recognition Result",
                    "confidence": 0.88,
                    "box": [[50, 100], [min(450, width-50), 100], [min(450, width-50), 130], [50, 130]]
                },
                {
                    "text": f"Image size: {width}x{height}",
                    "confidence": 0.92,
                    "box": [[50, 150], [min(300, width-50), 150], [min(300, width-50), 180], [50, 180]]
                }
            ]
            
            logger.info(f"🎭 Mock OCR completed: {len(mock_result)} text regions generated")
            return mock_result
            
        except Exception as e:
            logger.error(f"❌ Mock OCR prediction failed: {e}")
            raise


class OCRService:
    """OCR Service for processing images and extracting text"""
    
    def __init__(self):
        self.ocr_engine = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize OCR engine"""
        try:
            self.ocr_engine = OCREngine(
                use_textline_orientation=settings.PADDLEOCR_USE_ANGLE_CLS,
                lang=settings.PADDLEOCR_DEFAULT_LANG,
                use_gpu=settings.PADDLEOCR_USE_GPU
            )
            
            logger.info("OCR Engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OCR engine: {e}")
            raise RuntimeError(f"OCR engine initialization failed: {e}")
    
    async def validate_image(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Validate uploaded image file"""
        try:
            # Check file size
            if len(file_content) > settings.OCR_MAX_FILE_SIZE:
                raise ValueError(f"File size too large: {len(file_content)} bytes")
            
            # Check file format
            file_ext = Path(filename).suffix.lower().lstrip('.')
            if file_ext not in settings.ocr_allowed_formats_list:
                raise ValueError(f"Unsupported format: {file_ext}")
            
            # Validate image using PIL
            try:
                image = Image.open(BytesIO(file_content))
                image.verify()
            except Exception:
                raise ValueError("Invalid image file")
            
            return {
                "valid": True,
                "file_size": len(file_content),
                "format": file_ext,
                "filename": filename
            }
            
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def upload_to_r2(self, file_content: bytes, filename: str) -> str:
        """Upload file to R2 storage"""
        try:
            # Get file format
            file_ext = Path(filename).suffix.lower().lstrip('.')
            
            # Upload original image to R2
            _, public_url = r2_storage.upload_image(
                image_content=file_content,
                image_format=file_ext,
                prefix="ocr/original"
            )
            
            logger.info(f"File uploaded to R2: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload to R2: {e}")
            raise
    
    async def save_to_temp_file(self, file_content: bytes, filename: str) -> str:
        """Save file to temporary location for OCR processing"""
        try:
            # Create temporary file
            file_ext = Path(filename).suffix.lower()
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            logger.info(f"File saved to temporary location: {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            logger.error(f"Failed to save temporary file: {e}")
            raise
    
    async def process_ocr(
        self, 
        image_path: str, 
        language: str = "ch",
        use_angle_cls: bool = False,
        confidence_thresh: float = 0.5,
        ocr_record_id: str = None
    ) -> Dict[str, Any]:
        """Process OCR on image file with timeout handling"""
        try:
            start_time = datetime.utcnow()
            
            # Reinitialize engine if language changed
            if language != settings.PADDLEOCR_DEFAULT_LANG:
                self.ocr_engine = OCREngine(
                    use_textline_orientation=use_angle_cls,
                    lang=language,
                    use_gpu=settings.PADDLEOCR_USE_GPU
                )
            
            # Run OCR in thread pool to avoid blocking with timeout
            def run_ocr():
                return self.ocr_engine.predict(image_path)
            
            loop = asyncio.get_event_loop()
            
            try:
                # Set 30 second timeout for OCR processing
                ocr_results = await asyncio.wait_for(
                    loop.run_in_executor(None, run_ocr),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.error("❌ OCR processing timeout after 30 seconds")
                
                # Update database record status to failed if record_id provided
                if ocr_record_id:
                    await self._update_ocr_record_status(
                        ocr_record_id, 
                        status="failed", 
                        error_message="ocr识别调用超时"
                    )
                
                return {
                    "success": False,
                    "error": "ocr识别调用超时",
                    "processing_time": 30.0,
                    "timeout": True
                }
            except Exception as e:
                logger.error(f"❌ OCR processing failed: {e}")
                
                # Update database record status to failed if record_id provided
                if ocr_record_id:
                    await self._update_ocr_record_status(
                        ocr_record_id, 
                        status="failed", 
                        error_message=str(e)
                    )
                
                return {
                    "success": False,
                    "error": str(e),
                    "processing_time": (datetime.utcnow() - start_time).total_seconds()
                }
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            # 处理结果
            detection_boxes = []
            all_text = []
            confidences = []
            
            for result in ocr_results:
                if result["confidence"] >= confidence_thresh:
                    detection_boxes.append({
                        "text": result["text"],
                        "confidence": result["confidence"],
                        "box": result["box"]
                    })
                    all_text.append(result["text"])
                    confidences.append(result["confidence"])
            
            # 计算平均置信度
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # 合并所有文本
            combined_text = "\n".join(all_text)
            
            # 处理结果图片和JSON数据
            result_image_url = ""
            ocr_json_text = combined_text
            
            # 优先使用PaddleOCR生成的结果图片
            if hasattr(self.ocr_engine, 'result_image_path') and self.ocr_engine.result_image_path and os.path.exists(self.ocr_engine.result_image_path):
                try:
                    with open(self.ocr_engine.result_image_path, 'rb') as f:
                        image_bytes = f.read()
                        
                    # 上传到R2存储
                    _, result_image_url = r2_storage.upload_image(
                        image_content=image_bytes,
                        image_format='jpg',
                        prefix="ocr/results"
                    )
                    logger.info(f"✅ 已上传PaddleOCR结果图片到R2: {result_image_url}")
                except Exception as e:
                    logger.warning(f"⚠️ 上传PaddleOCR结果图片失败: {e}")
                    result_image_url = ""
            
            # 只有在PaddleOCR没有生成结果图片时，才手动生成
            if not result_image_url:
                logger.info("🎨 PaddleOCR未生成结果图片，使用自定义方式生成")
                result_image_url = await self.generate_result_image(image_path, detection_boxes)
            else:
                logger.info("✅ 使用PaddleOCR生成的结果图片，跳过自定义生成")
            
            # 处理JSON结果
            if hasattr(self.ocr_engine, 'result_json_path') and self.ocr_engine.result_json_path:
                try:
                    with open(self.ocr_engine.result_json_path, 'r', encoding='utf-8') as f:
                        ocr_json_text = f.read()
                    logger.info(f"✅ 已读取OCR结果JSON")
                except Exception as e:
                    logger.warning(f"⚠️ 读取JSON结果失败: {e}")
                    # 如果读取失败，使用默认的combined_text
            
            # 清理临时目录
            if hasattr(self.ocr_engine, 'temp_dir') and self.ocr_engine.temp_dir:
                try:
                    import shutil
                    shutil.rmtree(self.ocr_engine.temp_dir, ignore_errors=True)
                    logger.info(f"🧹 已清理临时目录: {self.ocr_engine.temp_dir}")
                except Exception as e:
                    logger.warning(f"⚠️ 清理临时目录失败: {e}")
            
            return {
                "success": True,
                "ocr_text": ocr_json_text,
                "ocr_confidence": avg_confidence,
                "detection_boxes": detection_boxes,
                "processing_time": processing_time,
                "total_boxes": len(detection_boxes),
                "result_image_url": result_image_url
            }
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": 0
            }
    
    async def generate_result_image(self, image_path: str, detection_boxes: List[Dict]) -> str:
        """Generate result image with bounding boxes and upload to R2"""
        try:
            # Read original image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Could not read image")
            
            # Draw bounding boxes
            for box_info in detection_boxes:
                box = box_info["box"]
                text = box_info["text"]
                confidence = box_info["confidence"]
                
                try:
                    # Validate and convert box coordinates to integers
                    if not box or len(box) < 4:
                        continue
                    
                    # Ensure all coordinates are numeric
                    valid_box = []
                    for point in box:
                        if isinstance(point, (list, tuple)) and len(point) >= 2:
                            try:
                                x = int(float(point[0]))
                                y = int(float(point[1]))
                                valid_box.append([x, y])
                            except (ValueError, TypeError):
                                # Skip invalid coordinates
                                break
                    
                    if len(valid_box) < 4:
                        # Skip this box if we don't have enough valid points
                        continue
                    
                    # Convert box coordinates to numpy array
                    pts = np.array(valid_box, np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    
                    # Draw bounding box
                    cv2.polylines(image, [pts], True, (0, 255, 0), 2)
                    
                    # Add confidence label
                    cv2.putText(
                        image, 
                        f"{confidence:.2f}", 
                        (pts[0][0][0], pts[0][0][1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.5, 
                        (0, 255, 0), 
                        1
                    )
                
                except Exception as box_error:
                    logger.warning(f"Failed to draw box for text '{text}': {box_error}")
                    continue
            
            # Encode image to bytes
            _, buffer = cv2.imencode('.jpg', image)
            result_image_bytes = buffer.tobytes()
            
            # Upload result image to R2
            _, result_url = r2_storage.upload_image(
                image_content=result_image_bytes,
                image_format='jpg',
                prefix="ocr/results"
            )
            
            logger.info(f"Result image uploaded to R2: {result_url}")
            return result_url
            
        except Exception as e:
            logger.error(f"Failed to generate result image: {e}")
            return ""  # Return empty string if failed
    
    async def _update_ocr_record_status(self, record_id: str, status: str, error_message: str = None):
        """Update OCR record status in database"""
        try:
            from app.crud import crud_ocr_record
            from app.db.session import SessionLocal
            
            db = SessionLocal()
            try:
                # Find the OCR record
                ocr_record = crud_ocr_record.get(db, id=record_id)
                if ocr_record:
                    # Update status and error message
                    update_data = {"status": status}
                    if error_message:
                        update_data["error_message"] = error_message
                    
                    crud_ocr_record.update(db, db_obj=ocr_record, obj_in=update_data)
                    db.commit()
                    logger.info(f"✅ Updated OCR record {record_id} status to {status}")
                else:
                    logger.warning(f"⚠️ OCR record {record_id} not found")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Failed to update OCR record status: {e}")

    async def cleanup_temp_files(self, *file_paths: str):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {file_path}: {e}")


# Global OCR service instance
ocr_service = OCRService() 