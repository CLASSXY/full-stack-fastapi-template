"""
OCR配置示例文件

如果你的settings配置有问题，可以参考这个文件进行配置
"""

# PaddleOCR配置
PADDLEOCR_USE_ANGLE_CLS = True  # 是否使用文本方向分类
PADDLEOCR_DEFAULT_LANG = "ch"   # 默认语言：ch(中文), en(英文)
PADDLEOCR_USE_GPU = False       # 是否使用GPU加速

# OCR文件限制
OCR_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
OCR_ALLOWED_FORMATS = "jpg,jpeg,png,bmp,tiff,webp"

# 转换为列表格式
ocr_allowed_formats_list = OCR_ALLOWED_FORMATS.split(",")

# 如果你的项目中没有这些配置，可以将以下代码添加到你的settings.py中：
"""
# OCR相关配置
PADDLEOCR_USE_ANGLE_CLS: bool = True
PADDLEOCR_DEFAULT_LANG: str = "ch"
PADDLEOCR_USE_GPU: bool = False
OCR_MAX_FILE_SIZE: int = 10 * 1024 * 1024
OCR_ALLOWED_FORMATS: str = "jpg,jpeg,png,bmp,tiff,webp"

@property
def ocr_allowed_formats_list(self) -> List[str]:
    return self.OCR_ALLOWED_FORMATS.split(",")
"""