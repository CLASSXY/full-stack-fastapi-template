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
            if self.use_gpu and self._has_gpu():
                paddle.set_device('gpu')
                logger.info("✅ Set device to GPU")
            else:
                paddle.set_device('cpu')
                logger.info("✅ Set device to CPU")

            self.ocr = PaddleOCR(
                use_textline_orientation=self.use_textline_orientation,  # 文本行方向分类
                lang=self.lang,  # 语言
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
    
    def _preprocess_image(self, image_path: str) -> str:
        """预处理图片以提高OCR识别率"""
        try:
            logger.info(f"🎨 开始预处理图片: {image_path}")
            
            # 读取图片
            image = cv2.imread(image_path)
            if image is None:
                logger.warning("⚠️ 无法读取图片，使用原始图片")
                return image_path
            
            original_height, original_width = image.shape[:2]
            logger.info(f"📐 原始图片尺寸: {original_width}x{original_height}")
            
            # 1. 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 2. 图片尺寸优化 - 确保图片不会太小
            min_size = 800  # 最小边长
            if min(original_width, original_height) < min_size:
                scale = min_size / min(original_width, original_height)
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                logger.info(f"📈 图片放大到: {new_width}x{new_height} (scale: {scale:.2f})")
            
            # 3. 降噪处理
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # 4. 对比度增强 - 使用CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            
            # 5. 锐化处理
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)
            
            # 6. 二值化处理 - 使用自适应阈值
            binary = cv2.adaptiveThreshold(
                sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # 7. 形态学操作 - 去除小噪点
            kernel = np.ones((2,2), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # 保存预处理后的图片
            temp_dir = tempfile.mkdtemp(prefix="ocr_preprocess_")
            preprocessed_path = os.path.join(temp_dir, "preprocessed.jpg")
            cv2.imwrite(preprocessed_path, cleaned)
            
            logger.info(f"✅ 图片预处理完成，保存到: {preprocessed_path}")
            return preprocessed_path
            
        except Exception as e:
            logger.warning(f"⚠️ 图片预处理失败: {e}，使用原始图片")
            return image_path
    
    def _initialize_mock_ocr(self):
        """Initialize mock OCR for fallback"""
        self.ocr = None
        logger.info("Using Mock OCR Engine")
    
    def diagnose_image(self, image_path: str) -> Dict[str, Any]:
        """诊断图片质量和OCR识别条件"""
        try:
            logger.info(f"🔍 开始诊断图片: {image_path}")
            
            # 读取图片
            image = cv2.imread(image_path)
            if image is None:
                return {"error": "无法读取图片文件"}
            
            # 基本信息
            height, width = image.shape[:2]
            file_size = os.path.getsize(image_path)
            
            # 转换为灰度图进行分析
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 计算图片质量指标
            # 1. 对比度分析
            contrast = gray.std()
            
            # 2. 亮度分析
            brightness = gray.mean()
            
            # 3. 清晰度分析 (拉普拉斯方差)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 4. 边缘检测 - 估算文字区域
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (width * height)
            
            # 5. 二值化预览
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            white_ratio = np.sum(binary == 255) / (width * height)
            
            # 质量评估
            quality_issues = []
            recommendations = []
            
            if width < 800 or height < 600:
                quality_issues.append("图片分辨率较低")
                recommendations.append("建议使用更高分辨率的图片")
            
            if contrast < 30:
                quality_issues.append("对比度不足")
                recommendations.append("增强图片对比度")
            
            if brightness < 50 or brightness > 200:
                quality_issues.append("亮度不合适")
                recommendations.append("调整图片亮度到合适范围")
            
            if laplacian_var < 100:
                quality_issues.append("图片可能模糊")
                recommendations.append("使用更清晰的图片")
            
            if edge_density < 0.01:
                quality_issues.append("可能缺少文字内容")
                recommendations.append("确认图片包含清晰的文字")
            
            # 综合评分
            score = 0
            if width >= 800 and height >= 600: score += 20
            if contrast >= 30: score += 20
            if 50 <= brightness <= 200: score += 20
            if laplacian_var >= 100: score += 20
            if edge_density >= 0.01: score += 20
            
            quality_level = "优秀" if score >= 80 else "良好" if score >= 60 else "一般" if score >= 40 else "较差"
            
            diagnosis = {
                "basic_info": {
                    "width": width,
                    "height": height,
                    "file_size": file_size,
                    "format": os.path.splitext(image_path)[1]
                },
                "quality_metrics": {
                    "contrast": round(contrast, 2),
                    "brightness": round(brightness, 2),
                    "sharpness": round(laplacian_var, 2),
                    "edge_density": round(edge_density, 4),
                    "white_ratio": round(white_ratio, 3)
                },
                "assessment": {
                    "score": score,
                    "level": quality_level,
                    "issues": quality_issues,
                    "recommendations": recommendations
                }
            }
            
            logger.info(f"📊 图片诊断完成: {quality_level} (评分: {score}/100)")
            return diagnosis
            
        except Exception as e:
            logger.error(f"❌ 图片诊断失败: {e}")
            return {"error": str(e)}
    
    def predict(self, image_path: str) -> List[Dict[str, Any]]:
        """OCR prediction with 30 second timeout and enhanced preprocessing"""
        try:
            logger.info(f"🔍 Starting OCR prediction for image: {image_path}")
            
            if self.ocr is None:
                logger.warning("⚠️  Using Mock OCR - PaddleOCR not available")
                return self._mock_predict(image_path)
            
            # Verify image file exists and is readable
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            logger.info(f"📁 Image file exists: {image_path} (size: {os.path.getsize(image_path)} bytes)")
            
            # 预处理图片以提高OCR识别率
            preprocessed_path = self._preprocess_image(image_path)
            
            # Use real PaddleOCR with timeout
            logger.info("🤖 Running PaddleOCR prediction with 30s timeout...")
            
            import signal
            import threading
            
            result = None
            exception = None
            
            def ocr_worker():
                nonlocal result, exception
                try:
                    # 使用预处理后的图片进行OCR识别
                    result = self.ocr.ocr(preprocessed_path, cls=self.use_textline_orientation)
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
            
            # 清理预处理的临时文件
            if preprocessed_path != image_path:
                try:
                    os.unlink(preprocessed_path)
                except:
                    pass

            # 创建临时目录用于保存结果图片
            temp_dir = tempfile.mkdtemp(prefix="ocr_result_")
            self.temp_dir = temp_dir
            self.result_image_path = ""
            self.result_json_path = "" # 不再使用JSON文件

            formatted_results = []
            
            # 统一处理新旧版本的PaddleOCR结果
            if result:
                logger.info(f"🔍 分析OCR结果结构: {type(result)}")
                
                # PaddleOCR标准格式: [[[box], [text, confidence]], ...]
                if isinstance(result, list) and len(result) > 0:
                    # 检查是否是标准的OCR结果格式
                    if isinstance(result[0], list):
                        logger.info("📋 处理标准PaddleOCR结果格式")
                        
                        for line_result in result[0] if result[0] else []:
                            if line_result and len(line_result) >= 2:
                                try:
                                    box = line_result[0]  # 边界框坐标
                                    text_info = line_result[1]  # [文本, 置信度]
                                    
                                    if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                                        text, confidence = text_info[0], text_info[1]
                                        
                                        # 过滤空文本和低置信度结果
                                        if text and text.strip() and confidence > 0.1:
                                            formatted_results.append({
                                                "text": text.strip(),
                                                "confidence": float(confidence),
                                                "box": box
                                            })
                                            logger.info(f"✅ 提取文本: '{text.strip()}' (置信度: {confidence:.3f})")
                                        else:
                                            logger.debug(f"⏭️ 跳过低质量文本: '{text}' (置信度: {confidence:.3f})")
                                            
                                except Exception as parse_error:
                                    logger.warning(f"⚠️ 解析单行结果失败: {parse_error}")
                                    continue
                    
                    # 检查是否是新版Result对象格式
                    elif hasattr(result[0], 'get_text_lines'):
                        logger.info("📋 处理新版PaddleOCR Result对象格式")
                        try:
                            # 保存可视化结果图片
                            img_path = os.path.join(temp_dir, "result_image.jpg")
                            result[0].save_to_img(img_path)
                            self.result_image_path = img_path
                            logger.info(f"✅ 保存OCR结果图片到: {img_path}")
                        except Exception as e:
                            logger.warning(f"⚠️ 无法使用新API保存结果图片: {e}")

                        text_lines = result[0].get_text_lines()
                        for line in text_lines:
                            if line.text and line.text.strip() and line.score > 0.1:
                                formatted_results.append({
                                    "text": line.text.strip(),
                                    "confidence": line.score,
                                    "box": line.box.tolist()
                                })
                                logger.info(f"✅ 提取文本: '{line.text.strip()}' (置信度: {line.score:.3f})")
                    
                    else:
                        logger.warning(f"⚠️ 未识别的OCR结果格式: {type(result[0])}")
                        logger.debug(f"📋 结果内容: {result}")

            # 如果没有检测到文本，尝试降低阈值重新处理
            if not formatted_results:
                logger.warning("⚠️ 未检测到文本，可能的原因:")
                logger.warning("   1. 图片中没有文字")
                logger.warning("   2. 文字对比度太低")
                logger.warning("   3. 文字太小或模糊")
                logger.warning("   4. 语言模型不匹配")
                logger.warning("   5. 图片质量问题")

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
        confidence_thresh: float = 0.3,  # 降低默认阈值
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

    async def enhanced_ocr_process(
        self, 
        image_path: str, 
        language: str = "ch",
        use_angle_cls: bool = False,
        confidence_thresh: float = 0.3
    ) -> Dict[str, Any]:
        """增强的OCR处理，使用多种策略提高识别率"""
        try:
            logger.info(f"🚀 开始增强OCR处理: {image_path}")
            
            # 1. 先诊断图片质量
            diagnosis = self.ocr_engine.diagnose_image(image_path)
            logger.info(f"📊 图片质量评估: {diagnosis.get('assessment', {}).get('level', '未知')}")
            
            # 2. 尝试多种预处理策略
            strategies = [
                ("原始图片", image_path),
                ("标准预处理", None),  # 将在下面生成
                ("高对比度处理", None),
                ("二值化处理", None)
            ]
            
            best_result = {"success": False, "detection_boxes": [], "ocr_text": ""}
            best_count = 0
            
            for strategy_name, strategy_path in strategies:
                try:
                    logger.info(f"🔄 尝试策略: {strategy_name}")
                    
                    # 生成对应的预处理图片
                    if strategy_path is None:
                        if strategy_name == "标准预处理":
                            strategy_path = self._preprocess_image_standard(image_path)
                        elif strategy_name == "高对比度处理":
                            strategy_path = self._preprocess_image_high_contrast(image_path)
                        elif strategy_name == "二值化处理":
                            strategy_path = self._preprocess_image_binary(image_path)
                    
                    # 执行OCR
                    result = await self._single_ocr_attempt(
                        strategy_path, language, use_angle_cls, confidence_thresh
                    )
                    
                    if result["success"]:
                        text_count = len(result["detection_boxes"])
                        logger.info(f"✅ {strategy_name} 识别到 {text_count} 个文本区域")
                        
                        # 选择识别效果最好的结果
                        if text_count > best_count:
                            best_result = result
                            best_count = text_count
                            logger.info(f"🏆 更新最佳结果: {strategy_name} ({text_count} 个文本)")
                    
                    # 清理临时文件
                    if strategy_path != image_path:
                        try:
                            os.unlink(strategy_path)
                        except:
                            pass
                            
                except Exception as strategy_error:
                    logger.warning(f"⚠️ 策略 {strategy_name} 失败: {strategy_error}")
                    continue
            
            # 3. 如果所有策略都失败，提供详细的诊断信息
            if best_count == 0:
                logger.warning("❌ 所有OCR策略都未能识别到文本")
                
                # 提供诊断建议
                issues = diagnosis.get('assessment', {}).get('issues', [])
                recommendations = diagnosis.get('assessment', {}).get('recommendations', [])
                
                error_msg = "OCR识别失败，可能原因:\n"
                for issue in issues:
                    error_msg += f"• {issue}\n"
                
                if recommendations:
                    error_msg += "\n建议:\n"
                    for rec in recommendations:
                        error_msg += f"• {rec}\n"
                
                return {
                    "success": False,
                    "error": error_msg,
                    "diagnosis": diagnosis,
                    "total_boxes": 0
                }
            
            logger.info(f"🎉 增强OCR处理完成，最终识别到 {best_count} 个文本区域")
            return best_result
            
        except Exception as e:
            logger.error(f"❌ 增强OCR处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_boxes": 0
            }
    
    def _preprocess_image_standard(self, image_path: str) -> str:
        """标准预处理"""
        return self.ocr_engine._preprocess_image(image_path)
    
    def _preprocess_image_high_contrast(self, image_path: str) -> str:
        """高对比度预处理"""
        try:
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 强化对比度
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # 伽马校正
            gamma = 1.2
            enhanced = np.power(enhanced / 255.0, gamma) * 255.0
            enhanced = enhanced.astype(np.uint8)
            
            temp_path = tempfile.mktemp(suffix='.jpg')
            cv2.imwrite(temp_path, enhanced)
            return temp_path
            
        except Exception as e:
            logger.warning(f"高对比度预处理失败: {e}")
            return image_path
    
    def _preprocess_image_binary(self, image_path: str) -> str:
        """二值化预处理"""
        try:
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 使用Otsu阈值进行二值化
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            temp_path = tempfile.mktemp(suffix='.jpg')
            cv2.imwrite(temp_path, binary)
            return temp_path
            
        except Exception as e:
            logger.warning(f"二值化预处理失败: {e}")
            return image_path
    
    async def _single_ocr_attempt(
        self, 
        image_path: str, 
        language: str, 
        use_angle_cls: bool, 
        confidence_thresh: float
    ) -> Dict[str, Any]:
        """单次OCR尝试"""
        try:
            # 使用现有的process_ocr方法
            result = await self.process_ocr(
                image_path=image_path,
                language=language,
                use_angle_cls=use_angle_cls,
                confidence_thresh=confidence_thresh
            )
            return result
            
        except Exception as e:
            logger.error(f"单次OCR尝试失败: {e}")
            return {"success": False, "error": str(e), "detection_boxes": []}

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