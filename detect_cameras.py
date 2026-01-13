#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USB摄像头设备检测工具
用于检测Windows系统中可用的USB摄像头设备
"""

import subprocess
import platform
import json

def list_usb_cameras():
    """列出所有USB摄像头设备"""
    if platform.system() != "Windows":
        print("此工具仅支持Windows系统")
        return []
    
    try:
        # 使用配置文件中的FFmpeg路径
        from config import config
        ffmpeg_path = config.get_app_config('ffmpeg.custom_path') or 'ffmpeg'
        
        # 检查项目本地的FFmpeg路径
        import os
        project_ffmpeg_path = r"c:\Users\Administrator\Documents\trae_projects\opencv\camera\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
        if os.path.exists(project_ffmpeg_path):
            ffmpeg_path = project_ffmpeg_path
        
        print(f"使用FFmpeg路径: {ffmpeg_path}")
        
        # 使用FFmpeg列出dshow设备
        cmd = [ffmpeg_path, '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        cameras = []
        lines = result.stderr.split('\n')
        
        print("正在检测USB摄像头设备...")
        print("-" * 50)
        
        # 查找所有视频设备
        video_devices = []
        for line in lines:
            # 查找视频设备行
            if '"' in line and '(video)' in line:
                # 提取设备名称
                start = line.find('"')
                if start != -1:
                    end = line.find('"', start + 1)
                    if end != -1:
                        device_name = line[start + 1:end]
                        if '48MP USB Camera' in device_name:
                            video_devices.append(device_name)
                            print(f"发现摄像头: {device_name}")
        
        # 由于所有摄像头名称相同，我们需要使用不同的方法来区分它们
        # 在Windows中，相同型号的摄像头可以通过索引来区分
        if video_devices:
            # 为每个摄像头创建唯一的标识符
            for i, device_name in enumerate(video_devices):
                # 使用设备名称+索引的方式
                unique_name = f"{device_name} #{i+1}"
                cameras.append(unique_name)
                print(f"摄像头 {i+1}: {unique_name}")
        
        # 如果没有找到任何摄像头，尝试备用方法
        if not cameras:
            # 尝试直接列出所有视频设备，不限制品牌
            for line in lines:
                if '"' in line and '(video)' in line:
                    start = line.find('"')
                    if start != -1:
                        end = line.find('"', start + 1)
                        if end != -1:
                            device_name = line[start + 1:end]
                            if device_name not in cameras:
                                cameras.append(device_name)
                                print(f"发现视频设备: {device_name}")
        
        if not cameras:
            print("未找到USB摄像头设备")
            print("请确保摄像头已连接并正确安装驱动程序")
        else:
            print(f"\n共发现 {len(cameras)} 个USB摄像头设备")
            
        return cameras
        
    except FileNotFoundError:
        print("错误: 未找到FFmpeg。请确保FFmpeg已安装并在系统PATH中")
        return []
    except Exception as e:
        print(f"检测失败: {e}")
        return []

def generate_config(cameras):
    """生成摄像头配置文件"""
    if not cameras:
        return None
    
    config = []
    for i, camera_name in enumerate(cameras[:4]):  # 最多4个摄像头
        config.append({
            "id": i,
            "name": f"USB摄像头{i+1}",
            "url": f"video={camera_name}",
            "enabled": True,
            "resolution": "640x480",
            "fps": 30,
            "type": "usb"
        })
    
    return config

def main():
    """主函数"""
    print("=== USB摄像头设备检测工具 ===")
    print(f"操作系统: {platform.system()}")
    print(f"Python版本: {platform.python_version()}")
    print()
    
    # 检测摄像头
    cameras = list_usb_cameras()
    
    if cameras:
        print("\n=== 生成配置文件 ===")
        config = generate_config(cameras)
        
        if config:
            print("\n建议的摄像头配置:")
            print(json.dumps(config, indent=2, ensure_ascii=False))
            
            print("\n=== 使用说明 ===")
            print("1. 将上述配置复制到 config.json 文件中")
            print("2. 替换 'cameras' 部分的配置")
            print("3. 重新启动应用程序")
            print("\n配置文件路径: d:/LLM/Xiangya/cv-catch/ffmpeg_cat/config.json")
    
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()