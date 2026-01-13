#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动脚本 - 四路摄像头实时监控系统
"""

import sys
import os
import subprocess
import platform

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 7):
        print("错误: 需要Python 3.7或更高版本")
        return False
    return True

def check_dependencies():
    """检查依赖库"""
    try:
        import PyQt5
        import numpy
        print("✓ PyQt5 已安装")
        print("✓ numpy 已安装")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖库: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def check_ffmpeg():
    """检查FFmpeg安装 - 支持项目本地路径"""
    # 尝试的FFmpeg路径列表
    ffmpeg_paths = []
    
    # 如果是打包后的exe，从临时目录查找
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
        ffmpeg_paths.append(os.path.join(bundle_dir, 'ffmpeg', 'ffmpeg.exe'))
    
    # 项目本地FFmpeg路径
    ffmpeg_paths.append(r"C:\Users\Administrator\Desktop\xy\ffmpeg_cat\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe")
    # 系统PATH中的FFmpeg
    ffmpeg_paths.append("ffmpeg")
    
    for ffmpeg_path in ffmpeg_paths:
        try:
            result = subprocess.run([ffmpeg_path, '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # 提取版本信息
                version_line = result.stdout.split('\n')[0]
                print(f"✓ FFmpeg 已安装: {version_line}")
                print(f"  路径: {ffmpeg_path}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    print("✗ FFmpeg 未安装或未找到")
    print("请安装FFmpeg:")
    print("  Windows: 下载并安装FFmpeg，添加到PATH")
    print("  Linux: sudo apt-get install ffmpeg")
    print("  macOS: brew install ffmpeg")
    return False

def main():
    """主函数"""
    print("四路摄像头实时监控系统 - 启动检查")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        return 1
    print(f"✓ Python版本: {sys.version}")
    
    # 检查依赖库
    print("\n检查依赖库...")
    if not check_dependencies():
        return 1
    
    # 检查FFmpeg
    print("\n检查FFmpeg...")
    if not check_ffmpeg():
        return 1
    
    print("\n" + "=" * 50)
    print("✓ 所有检查通过！")
    print("正在启动主程序...")
    
    try:
        # 导入并运行主程序
        from main import main as app_main
        return app_main()
    except Exception as e:
        print(f"启动主程序失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())