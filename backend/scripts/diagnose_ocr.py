#!/usr/bin/env python3
"""
OCR诊断脚本 - 用于排查PaddleOCR安装和配置问题
"""

import sys
import os
import subprocess
import importlib
import tempfile
from pathlib import Path

def print_section(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def check_python_version():
    print_section("Python版本检查")
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")

def check_system_dependencies():
    print_section("系统依赖检查")
    
    # 检查关键的系统库
    required_libs = [
        'libgl1-mesa-glx',
        'libglib2.0-0', 
        'libsm6',
        'libxext6',
        'libxrender-dev',
        'libgomp1'
    ]
    
    for lib in required_libs:
        try:
            result = subprocess.run(['dpkg', '-l', lib], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {lib}: 已安装")
            else:
                print(f"❌ {lib}: 未安装")
        except Exception as e:
            print(f"⚠️ 无法检查 {lib}: {e}")

def check_python_packages():
    print_section("Python包检查")
    
    required_packages = [
        'numpy',
        'opencv-python', 
        'Pillow',
        'paddlepaddle',
        'paddleocr'
    ]
    
    for package in required_packages:
        try:
            module = importlib.import_module(package.replace('-', '_'))
            version = getattr(module, '__version__', 'unknown')
            print(f"✅ {package}: {version}")
        except ImportError as e:
            print(f"❌ {package}: 未安装 - {e}")
        except Exception as e:
            print(f"⚠️ {package}: 检查失败 - {e}")

def check_paddle_installation():
    print_section("PaddlePaddle安装检查")
    
    try:
        import paddle
        print(f"✅ PaddlePaddle版本: {paddle.__version__}")
        print(f"✅ PaddlePaddle路径: {paddle.__file__}")
        
        # 检查设备支持
        try:
            device = paddle.device.get_device()
            print(f"✅ 当前设备: {device}")
        except Exception as e:
            print(f"⚠️ 设备检查失败: {e}")
            
        # 检查CUDA环境变量
        cuda_visible = os.environ.get('CUDA_VISIBLE_DEVICES', 'not set')
        print(f"📋 CUDA_VISIBLE_DEVICES: {cuda_visible}")
        
    except ImportError as e:
        print(f"❌ PaddlePaddle导入失败: {e}")
    except Exception as e:
        print(f"❌ PaddlePaddle检查失败: {e}")

def check_paddleocr_installation():
    print_section("PaddleOCR安装检查")
    
    try:
        import paddleocr
        print(f"✅ PaddleOCR版本: {paddleocr.__version__}")
        print(f"✅ PaddleOCR路径: {paddleocr.__file__}")
        
        # 检查PaddleOCR类是否可以导入
        from paddleocr import PaddleOCR
        print("✅ PaddleOCR类导入成功")
        
    except ImportError as e:
        print(f"❌ PaddleOCR导入失败: {e}")
    except Exception as e:
        print(f"❌ PaddleOCR检查失败: {e}")

def check_model_directories():
    print_section("模型目录检查")
    
    # 检查环境变量设置的模型目录
    hub_home = os.environ.get('HUB_HOME', '/app/paddleocr_models')
    paddlehub_home = os.environ.get('PADDLEHUB_HOME', '/app/paddleocr_models')
    
    print(f"📋 HUB_HOME: {hub_home}")
    print(f"📋 PADDLEHUB_HOME: {paddlehub_home}")
    
    # 检查目录是否存在和权限
    for path_name, path_value in [('HUB_HOME', hub_home), ('PADDLEHUB_HOME', paddlehub_home)]:
        if os.path.exists(path_value):
            print(f"✅ {path_name}目录存在: {path_value}")
            
            # 检查权限
            if os.access(path_value, os.R_OK):
                print(f"✅ {path_name}可读")
            else:
                print(f"❌ {path_name}不可读")
                
            if os.access(path_value, os.W_OK):
                print(f"✅ {path_name}可写")
            else:
                print(f"❌ {path_name}不可写")
                
            # 列出目录内容
            try:
                contents = os.listdir(path_value)
                if contents:
                    print(f"📋 {path_name}内容: {contents[:5]}{'...' if len(contents) > 5 else ''}")
                else:
                    print(f"📋 {path_name}为空")
            except Exception as e:
                print(f"⚠️ 无法列出{path_name}内容: {e}")
        else:
            print(f"❌ {path_name}目录不存在: {path_value}")

def test_paddleocr_initialization():
    print_section("PaddleOCR初始化测试")
    
    try:
        from paddleocr import PaddleOCR
        
        print("🔄 尝试初始化PaddleOCR...")
        
        # 使用最小配置初始化
        ocr = PaddleOCR(
            use_angle_cls=False,
            lang='ch',
            use_gpu=False,
            show_log=False
        )
        
        print("✅ PaddleOCR初始化成功")
        
        # 测试简单的OCR功能
        print("🔄 创建测试图片...")
        
        # 创建一个简单的测试图片
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
        
        # 创建白色背景图片
        img = Image.new('RGB', (200, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # 绘制文字
        try:
            # 尝试使用默认字体
            draw.text((10, 30), "测试文字", fill='black')
        except:
            # 如果字体加载失败，使用简单图形
            draw.rectangle([10, 30, 150, 60], outline='black', width=2)
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            img.save(tmp_file.name)
            test_image_path = tmp_file.name
        
        print(f"✅ 测试图片创建成功: {test_image_path}")
        
        # 运行OCR测试
        print("🔄 运行OCR测试...")
        result = ocr.ocr(test_image_path, cls=False)
        
        if result and len(result) > 0:
            print("✅ OCR测试成功")
            print(f"📋 识别结果: {result}")
        else:
            print("⚠️ OCR测试完成但无识别结果")
        
        # 清理临时文件
        try:
            os.unlink(test_image_path)
        except:
            pass
            
    except ImportError as e:
        print(f"❌ PaddleOCR导入失败: {e}")
    except Exception as e:
        print(f"❌ PaddleOCR初始化失败: {e}")
        import traceback
        print(f"详细错误信息:\n{traceback.format_exc()}")

def check_memory_usage():
    print_section("内存使用检查")
    
    try:
        import psutil
        
        # 获取内存信息
        memory = psutil.virtual_memory()
        print(f"📋 总内存: {memory.total / (1024**3):.2f} GB")
        print(f"📋 可用内存: {memory.available / (1024**3):.2f} GB")
        print(f"📋 内存使用率: {memory.percent}%")
        
        if memory.available < 1 * 1024**3:  # 小于1GB
            print("⚠️ 可用内存不足1GB，可能影响PaddleOCR运行")
        else:
            print("✅ 内存充足")
            
    except ImportError:
        print("⚠️ psutil未安装，无法检查内存使用")
    except Exception as e:
        print(f"⚠️ 内存检查失败: {e}")

def check_network_connectivity():
    print_section("网络连接检查")
    
    # 检查是否能访问PaddleOCR模型下载地址
    test_urls = [
        'https://paddleocr.bj.bcebos.com',
        'https://github.com/PaddlePaddle/PaddleOCR',
        'https://pypi.org'
    ]
    
    for url in test_urls:
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=10)
            print(f"✅ 可以访问: {url}")
        except Exception as e:
            print(f"❌ 无法访问: {url} - {e}")

def main():
    print("🔍 PaddleOCR诊断工具")
    print("=" * 60)
    
    check_python_version()
    check_system_dependencies()
    check_python_packages()
    check_paddle_installation()
    check_paddleocr_installation()
    check_model_directories()
    check_memory_usage()
    check_network_connectivity()
    test_paddleocr_initialization()
    
    print_section("诊断完成")
    print("请将以上输出发送给技术支持人员以获得进一步帮助。")

if __name__ == "__main__":
    main()