#!/usr/bin/env python3
"""
服务器OCR修复脚本
直接在服务器上运行此脚本来修复PaddleOCR兼容性问题
"""

import os
import sys
import subprocess
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def run_command(cmd, description=""):
    """运行命令并返回结果"""
    try:
        logger.info(f"🔧 {description}: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            logger.info(f"✅ {description} 成功")
            if result.stdout.strip():
                logger.info(f"输出: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"❌ {description} 失败")
            if result.stderr.strip():
                logger.error(f"错误: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"❌ {description} 超时")
        return False
    except Exception as e:
        logger.error(f"❌ {description} 异常: {e}")
        return False

def check_docker():
    """检查Docker是否可用"""
    return run_command("docker --version", "检查Docker版本")

def fix_ocr_in_container():
    """在Docker容器内修复OCR"""
    logger.info("🚀 开始在Docker容器内修复OCR...")
    
    # 检查容器是否运行
    if not run_command("docker compose -f docker-compose.backend.yml ps | grep -q 'Up'", "检查容器状态"):
        logger.error("❌ 后端容器未运行，请先启动服务")
        return False
    
    # 在容器内创建兼容性修复文件
    fix_script = '''
import paddle
import sys

try:
    # 修复PaddlePaddle 3.0兼容性问题
    if hasattr(paddle, 'base') and hasattr(paddle.base, 'libpaddle'):
        if hasattr(paddle.base.libpaddle, 'AnalysisConfig'):
            if not hasattr(paddle.base.libpaddle.AnalysisConfig, 'set_optimization_level'):
                paddle.base.libpaddle.AnalysisConfig.set_optimization_level = lambda self, level: None
                print('✅ Applied set_optimization_level fix')
    
    # 修复其他可能的兼容性问题
    if hasattr(paddle, 'fluid') and not hasattr(paddle.fluid, 'layers'):
        import paddle.nn as layers
        paddle.fluid.layers = layers
        print('✅ Applied fluid.layers fix')
        
    print('✅ PaddlePaddle兼容性修复应用成功')
    
    # 测试PaddleOCR初始化
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(use_angle_cls=False, lang='ch', use_gpu=False, show_log=False)
    print('✅ PaddleOCR初始化成功')
        
except Exception as e:
    print(f'❌ 修复失败: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
    
    # 在容器内执行修复
    cmd = f'docker compose -f docker-compose.backend.yml exec -T backend python -c "{fix_script}"'
    if run_command(cmd, "在容器内执行OCR修复"):
        logger.info("✅ 容器内OCR修复成功")
        return True
    else:
        logger.error("❌ 容器内OCR修复失败")
        return False

def restart_backend():
    """重启后端服务"""
    logger.info("🔄 重启后端服务...")
    return run_command("docker compose -f docker-compose.backend.yml restart backend", "重启后端容器")

def check_ocr_status():
    """检查OCR状态"""
    logger.info("🔍 检查OCR状态...")
    cmd = 'docker compose -f docker-compose.backend.yml logs backend | grep -E "(OCR|PaddleOCR|Mock)" | tail -10'
    run_command(cmd, "查看OCR相关日志")

def main():
    """主函数"""
    logger.info("🚀 开始OCR修复流程...")
    
    # 检查Docker
    if not check_docker():
        logger.error("❌ Docker不可用，请确保在有Docker的服务器环境中运行此脚本")
        sys.exit(1)
    
    # 修复OCR
    if fix_ocr_in_container():
        logger.info("✅ OCR修复完成")
        
        # 重启服务
        if restart_backend():
            logger.info("✅ 服务重启完成")
            
            # 等待服务启动
            logger.info("⏳ 等待服务启动...")
            import time
            time.sleep(10)
            
            # 检查状态
            check_ocr_status()
            
            logger.info("🎉 OCR修复流程完成！")
            logger.info("📋 请查看上面的日志确认OCR是否正常工作")
        else:
            logger.error("❌ 服务重启失败")
            sys.exit(1)
    else:
        logger.error("❌ OCR修复失败")
        sys.exit(1)

if __name__ == "__main__":
    main()