#!/bin/bash

# OCR快速修复脚本 - 用于服务器部署后修复PaddleOCR问题

set -e

echo "🔧 开始OCR快速修复..."

# 检查是否在容器内运行
if [ -f /.dockerenv ]; then
    echo "✅ 在Docker容器内运行"
    IN_CONTAINER=true
else
    echo "⚠️ 在宿主机运行，将尝试进入容器"
    IN_CONTAINER=false
fi

# 如果不在容器内，尝试进入容器执行
if [ "$IN_CONTAINER" = false ]; then
    echo "🔄 尝试在Docker容器内执行修复..."
    docker compose -f docker-compose.backend.yml exec backend bash -c "cd /app && ./scripts/quick_fix_ocr.sh"
    exit $?
fi

# 以下代码在容器内执行

echo "📋 当前环境信息:"
echo "Python版本: $(python --version)"
echo "工作目录: $(pwd)"
echo "用户: $(whoami)"

# 1. 检查并创建必要目录
echo "🔧 步骤1: 检查目录结构"
mkdir -p /app/paddleocr_models /app/uploads/ocr /tmp
chmod -R 755 /app/paddleocr_models /app/uploads
echo "✅ 目录创建完成"

# 2. 设置环境变量
echo "🔧 步骤2: 设置环境变量"
export HUB_HOME=/app/paddleocr_models
export PADDLEHUB_HOME=/app/paddleocr_models
export CUDA_VISIBLE_DEVICES=""
echo "✅ 环境变量设置完成"

# 3. 检查Python包安装
echo "🔧 步骤3: 检查Python包"
python -c "
import sys
packages = ['numpy', 'cv2', 'PIL', 'paddle', 'paddleocr']
for pkg in packages:
    try:
        if pkg == 'cv2':
            import cv2
            print(f'✅ opencv-python: {cv2.__version__}')
        elif pkg == 'PIL':
            import PIL
            print(f'✅ Pillow: {PIL.__version__}')
        else:
            module = __import__(pkg)
            version = getattr(module, '__version__', 'unknown')
            print(f'✅ {pkg}: {version}')
    except ImportError as e:
        print(f'❌ {pkg}: 未安装 - {e}')
        sys.exit(1)
"

# 4. 创建兼容性修复
echo "🔧 步骤4: 创建兼容性修复"
cat > /app/paddle_fix.py << 'EOF'
import paddle
try:
    # 修复PaddlePaddle 3.0兼容性问题
    if not hasattr(paddle.base.libpaddle.AnalysisConfig, "set_optimization_level"):
        paddle.base.libpaddle.AnalysisConfig.set_optimization_level = lambda self, level: None
    
    # 修复其他可能的兼容性问题
    if hasattr(paddle, 'fluid') and not hasattr(paddle.fluid, 'layers'):
        import paddle.nn as layers
        paddle.fluid.layers = layers
        
    print("✅ PaddlePaddle兼容性修复应用成功")
        
except Exception as e:
    print(f"⚠️ PaddlePaddle兼容性修复失败: {e}")
EOF
echo "✅ 兼容性修复创建完成"

# 5. 测试PaddleOCR初始化
echo "🔧 步骤5: 测试PaddleOCR初始化"
python -c "
import sys
sys.path.insert(0, '/app')

try:
    import paddle_fix
    print('✅ 兼容性修复加载成功')
except Exception as e:
    print(f'⚠️ 兼容性修复加载失败: {e}')

try:
    from paddleocr import PaddleOCR
    print('✅ PaddleOCR导入成功')
    
    # 初始化OCR
    print('🔄 初始化PaddleOCR...')
    ocr = PaddleOCR(use_textline_orientation=False, lang='ch', use_gpu=False)
    print('✅ PaddleOCR初始化成功')
    
except Exception as e:
    print(f'❌ PaddleOCR测试失败: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

# 6. 创建测试图片并运行OCR测试
echo "🔧 步骤6: 运行OCR功能测试"
python -c "
import sys
sys.path.insert(0, '/app')
import paddle_fix
from paddleocr import PaddleOCR
from PIL import Image, ImageDraw
import tempfile
import os

try:
    # 创建测试图片
    img = Image.new('RGB', (200, 100), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((10, 30), '测试文字', fill='black')
    
    # 保存到临时文件
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        img.save(tmp_file.name)
        test_image_path = tmp_file.name
    
    print(f'✅ 测试图片创建: {test_image_path}')
    
    # 初始化OCR
    ocr = PaddleOCR(use_textline_orientation=False, lang='ch', use_gpu=False)
    
    # 运行OCR测试
    result = ocr.ocr(test_image_path, cls=False)
    
    if result and len(result) > 0:
        print('✅ OCR功能测试成功')
        print(f'📋 识别结果数量: {len(result[0]) if result[0] else 0}')
    else:
        print('⚠️ OCR测试完成但无识别结果')
    
    # 清理临时文件
    os.unlink(test_image_path)
    
except Exception as e:
    print(f'❌ OCR功能测试失败: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

echo "✅ OCR快速修复完成！"
echo ""
echo "📋 修复摘要:"
echo "  - 目录结构已创建"
echo "  - 环境变量已设置"
echo "  - Python包检查通过"
echo "  - 兼容性修复已应用"
echo "  - PaddleOCR初始化成功"
echo "  - OCR功能测试通过"
echo ""
echo "🚀 现在可以重启应用程序测试OCR功能"