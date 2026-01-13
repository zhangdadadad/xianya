#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFmpeg安装检测和自动安装脚本
"""

import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import shutil
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_ffmpeg_in_path():
    """检查FFmpeg是否在PATH中"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def find_ffmpeg_in_common_locations():
    """在常见位置查找FFmpeg"""
    common_paths = []
    
    if platform.system() == "Windows":
        # Windows常见路径
        common_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'ffmpeg', 'bin', 'ffmpeg.exe'),
        ]
    else:
        # Linux/Mac常见路径
        common_paths = [
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            '/opt/ffmpeg/bin/ffmpeg',
            os.path.expanduser('~/bin/ffmpeg'),
        ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    return None

def download_ffmpeg_windows():
    """下载Windows版FFmpeg"""
    logger.info("正在下载Windows版FFmpeg...")
    
    # 创建安装目录
    install_dir = r"C:\ffmpeg"
    bin_dir = os.path.join(install_dir, "bin")
    
    try:
        os.makedirs(bin_dir, exist_ok=True)
        
        # 下载FFmpeg（使用GitHub镜像）
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        zip_path = os.path.join(install_dir, "ffmpeg.zip")
        
        logger.info(f"从 {url} 下载FFmpeg...")
        urllib.request.urlretrieve(url, zip_path)
        
        # 解压
        logger.info("解压FFmpeg...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(install_dir)
        
        # 找到bin目录
        extracted_dirs = [d for d in os.listdir(install_dir) 
                         if os.path.isdir(os.path.join(install_dir, d))]
        
        for dir_name in extracted_dirs:
            bin_path = os.path.join(install_dir, dir_name, "bin")
            if os.path.exists(bin_path) and os.path.exists(os.path.join(bin_path, "ffmpeg.exe")):
                # 复制到目标位置
                for file in os.listdir(bin_path):
                    src = os.path.join(bin_path, file)
                    dst = os.path.join(bin_dir, file)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                break
        
        # 清理
        os.remove(zip_path)
        for dir_name in extracted_dirs:
            shutil.rmtree(os.path.join(install_dir, dir_name), ignore_errors=True)
        
        logger.info(f"FFmpeg已安装到 {bin_dir}")
        return os.path.join(bin_dir, "ffmpeg.exe")
        
    except Exception as e:
        logger.error(f"下载FFmpeg失败: {e}")
        return None

def add_to_path_windows(ffmpeg_path):
    """将FFmpeg添加到Windows PATH"""
    try:
        import winreg
        
        bin_dir = os.path.dirname(ffmpeg_path)
        
        # 添加到用户PATH
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                            r"Environment", 0, winreg.KEY_ALL_ACCESS)
        
        try:
            current_path, _ = winreg.QueryValueEx(key, "Path")
        except WindowsError:
            current_path = ""
        
        if bin_dir not in current_path:
            new_path = current_path + ";" + bin_dir if current_path else bin_dir
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)
            
            logger.info(f"已将 {bin_dir} 添加到用户PATH")
            logger.info("请重新启动应用程序以使PATH更改生效")
            return True
        else:
            logger.info("FFmpeg已在PATH中")
            return True
            
    except Exception as e:
        logger.error(f"添加到PATH失败: {e}")
        return False

def install_ffmpeg():
    """自动安装FFmpeg"""
    logger.info("开始自动安装FFmpeg...")
    
    if platform.system() == "Windows":
        ffmpeg_path = download_ffmpeg_windows()
        if ffmpeg_path:
            return add_to_path_windows(ffmpeg_path)
    else:
        logger.info("请手动安装FFmpeg:")
        logger.info("Ubuntu/Debian: sudo apt-get install ffmpeg")
        logger.info("CentOS/RHEL: sudo yum install ffmpeg")
        logger.info("macOS: brew install ffmpeg")
        return False
    
    return False

def check_and_install_ffmpeg():
    """检查并安装FFmpeg"""
    logger.info("检查FFmpeg安装状态...")
    
    # 1. 检查PATH
    if check_ffmpeg_in_path():
        logger.info("✓ FFmpeg已在PATH中")
        return True
    
    # 2. 查找已安装的FFmpeg
    ffmpeg_path = find_ffmpeg_in_common_locations()
    if ffmpeg_path:
        logger.info(f"✓ 找到FFmpeg: {ffmpeg_path}")
        logger.info("正在添加到PATH...")
        
        if platform.system() == "Windows":
            return add_to_path_windows(ffmpeg_path)
        else:
            logger.info("请手动将FFmpeg添加到PATH")
            return False
    
    # 3. 自动安装
    logger.info("未找到FFmpeg，准备自动安装...")
    return install_ffmpeg()

def main():
    """主函数"""
    print("FFmpeg安装检测工具")
    print("=" * 50)
    
    success = check_and_install_ffmpeg()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ FFmpeg安装完成！")
        print("请重新启动您的应用程序")
    else:
        print("✗ FFmpeg安装失败")
        print("请手动安装FFmpeg或联系技术支持")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())