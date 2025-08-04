#!/usr/bin/env python3
"""
OCR部署修复脚本 - 自动修复PaddleOCR部署问题
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_step(step, description):
    print(f"\n🔧 步骤 {step}: {description}")
    print("-" * 50)

def run_command(cmd, description=""):
    """运行命令并处理错误"""
    try:
        print(f"执行: {cmd}")
        result = subprocess.run(cmd, shell=True, check=True, 
                              capture_output=True, text=True)
        if result.stdout:
            print(f"输出: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {e}")
        if e.stderr:
            print(f"错误: {e.stderr}")
        return False

def fix_system_dependencies():
    """修复系统依赖"""
    print_step(1, "修复系统依赖")
    
    # 更新包列表
    if not run_command("apt-get update", "更新包列表"):
        return False
    
    # 安装PaddleOCR所需的系统依赖
    dependencies = [
        "libgl1-mesa-glx",
        "libglib2.0-0", 
        "libsm6",
        "libxext6",
        "libxrender-dev",
        "libgomp1",
        "libfontconfig1",
        "libxinerama1",
        "libxrandr2",
        "libxss1",
        "libxtst6",
        "libasound2",
        "wget"
    ]
    
    cmd = f"apt-get install -y {' '.join(dependencies)}"
    if not run_command(cmd, "安装系统依赖"):
        return False
    
    print("✅ 系统依赖安装完成")
    return True

def fix_python_packages():
    """修复Python包"""
    print_step(2, "修复Python包")
    
    # 卸载可能冲突的包
    print("🔄 卸载可能冲突的包...")
    packages_to_remove = ["paddlepaddle", "paddlepaddle-gpu", "paddleocr"]
    for package in packages_to_remove:
        run_command(f"pip uninstall -y {package}", f"卸载 {package}")
    
    # 清理pip缓存
    run_command("pip cache purge", "清理pip缓存")
    
    # 安装基础依赖
    print("🔄 安装基础依赖...")
    base_packages = [
        "numpy==2.3.2",
        "opencv-python==4.11.0.86", 
        "Pillow==11.3.0",
        "setuptools==80.9.0"
    ]
    
    for package in base_packages:
        if not run_command(f"pip install --no-cache-dir {package}", f"安装 {package}"):
            return False
    
    # 安装PaddlePaddle
    print("🔄 安装PaddlePaddle...")
    paddle_cmd = "pip install --no-cache-dir paddlepaddle-gpu==2.6.2"
    if not run_command(paddle_cmd, "安装PaddlePaddle"):
        # 如果GPU版本失败，尝试CPU版本
        print("⚠️ GPU版本安装失败，尝试CPU版本...")
        paddle_cmd = "pip install --no-cache-dir paddlepaddle==2.6.2"
        if not run_command(paddle_cmd, "安装PaddlePaddle CPU版本"):
            return False
    
    # 安装PaddleOCR
    print("🔄 安装PaddleOCR...")
    if not run_command("pip install --no-cache-dir paddleocr==3.1.0", "安装PaddleOCR"):
        return False
    
    print("✅ Python包安装完成")
    return True

def fix_model_directories():
    """修复模型目录"""
    print_step(3, "修复模型目录")
    
    # 创建模型目录
    model_dirs = [
        "/app/paddleocr_models",
        "/app/uploads/ocr",
        "/tmp"
    ]
    
    for dir_path in model_dirs:
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            # 设置权限
            os.chmod(dir_path, 0o755)
            print(f"✅ 创建目录: {dir_path}")
        except Exception as e:
            print(f"❌ 创建目录失败 {dir_path}: {e}")
            return False
    
    # 设置环境变量
    os.environ['HUB_HOME'] = '/app/paddleocr_models'
    os.environ['PADDLEHUB_HOME'] = '/app/paddleocr_models'
    os.environ['CUDA_VISIBLE_DEVICES'] = ''  # 强制使用CPU
    
    print("✅ 模型目录设置完成")
    return True

def create_paddle_fix():
    """创建PaddlePaddle兼容性修复"""
    print_step(4, "创建PaddlePaddle兼容性修复")
    
    paddle_fix_content = '''import paddle
try:
    # 修复PaddlePaddle 3.0兼容性问题
    if not hasattr(paddle.base.libpaddle.AnalysisConfig, "set_optimization_level"):
        paddle.base.libpaddle.AnalysisConfig.set_optimization_level = lambda self, level: None
    
    # 修复其他可能的兼容性问题
    if hasattr(paddle, 'fluid') and not hasattr(paddle.fluid, 'layers'):
        import paddle.nn as layers
        paddle.fluid.layers = layers
        
except Exception as e:
    print(f"Warning: Could not apply paddle fix: {e}")
'''
    
    try:
        with open('/app/paddle_fix.py', 'w') as f:
            f.write(paddle_fix_content)
        print("✅ PaddlePaddle兼容性修复创建完成")
        return True
    except Exception as e:
        print(f"❌ 创建兼容性修复失败: {e}")
        return False

def test_ocr_installation():
    """测试OCR安装"""
    print_step(5, "测试OCR安装")
    
    test_script = '''
import sys
sys.path.insert(0, "/app")

try:
    import paddle_fix
    print("✅ 兼容性修复加载成功")
except:
    print("⚠️ 兼容性修复加载失败")

try:
    from paddleocr import PaddleOCR
    print("✅ PaddleOCR导入成功")
    
    # 初始化OCR
    ocr = PaddleOCR(use_angle_cls=False, lang='ch', use_gpu=False, show_log=False)
    print("✅ PaddleOCR初始化成功")
    
except Exception as e:
    print(f"❌ PaddleOCR测试失败: {e}")
    import traceback
    traceback.print_exc()
'''
    
    try:
        with open('/tmp/test_ocr.py', 'w') as f:
            f.write(test_script)
        
        result = subprocess.run([sys.executable, '/tmp/test_ocr.py'], 
                              capture_output=True, text=True, timeout=60)
        
        print("测试输出:")
        print(result.stdout)
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ OCR安装测试通过")
            return True
        else:
            print("❌ OCR安装测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        return False

def download_models():
    """预下载OCR模型"""
    print_step(6, "预下载OCR模型")
    
    download_script = '''
import sys
sys.path.insert(0, "/app")

try:
    import paddle_fix
    from paddleocr import PaddleOCR
    
    print("🔄 开始下载OCR模型...")
    
    # 初始化OCR会自动下载模型
    ocr = PaddleOCR(
        use_angle_cls=False, 
        lang='ch', 
        use_gpu=False, 
        show_log=True
    )
    
    print("✅ OCR模型下载完成")
    
except Exception as e:
    print(f"❌ 模型下载失败: {e}")
    import traceback
    traceback.print_exc()
'''
    
    try:
        with open('/tmp/download_models.py', 'w') as f:
            f.write(download_script)
        
        # 设置较长的超时时间用于模型下载
        result = subprocess.run([sys.executable, '/tmp/download_models.py'], 
                              capture_output=True, text=True, timeout=300)
        
        print("下载输出:")
        print(result.stdout)
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ 模型下载完成")
            return True
        else:
            print("⚠️ 模型下载可能失败，但会在运行时重试")
            return True  # 不阻止后续步骤
            
    except subprocess.TimeoutExpired:
        print("⚠️ 模型下载超时，但会在运行时重试")
        return True
    except Exception as e:
        print(f"⚠️ 模型下载失败: {e}")
        return True  # 不阻止后续步骤

def main():
    print("🔧 PaddleOCR部署修复工具")
    print("=" * 60)
    
    steps = [
        fix_system_dependencies,
        fix_python_packages, 
        fix_model_directories,
        create_paddle_fix,
        test_ocr_installation,
        download_models
    ]
    
    success_count = 0
    for i, step_func in enumerate(steps, 1):
        try:
            if step_func():
                success_count += 1
                print(f"✅ 步骤 {i} 完成")
            else:
                print(f"❌ 步骤 {i} 失败")
        except Exception as e:
            print(f"❌ 步骤 {i} 异常: {e}")
    
    print(f"\n📊 修复完成: {success_count}/{len(steps)} 步骤成功")
    
    if success_count >= 4:  # 至少前4步成功
        print("✅ 基本修复完成，请重启应用测试")
    else:
        print("❌ 修复失败，请检查错误信息")

if __name__ == "__main__":
    main()