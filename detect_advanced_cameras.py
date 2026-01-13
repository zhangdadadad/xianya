#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级摄像头检测工具
用于查找Windows系统中摄像头的完整设备信息，包括PNP路径
"""

import subprocess
import platform
import logging
import re

def get_detailed_camera_info():
    """获取详细的摄像头设备信息"""
    if platform.system() != "Windows":
        print("此工具仅支持Windows系统")
        return []
    
    try:
        # 检查项目本地的FFmpeg路径
        import os
        ffmpeg_path = 'ffmpeg'  # 默认使用系统PATH中的ffmpeg
        project_ffmpeg_path = r"c:\Users\Administrator\Documents\trae_projects\opencv\camera\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
        if os.path.exists(project_ffmpeg_path):
            ffmpeg_path = project_ffmpeg_path
        
        # 使用FFmpeg列出详细的dshow设备信息
        cmd = [ffmpeg_path, '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        print("FFmpeg设备列表输出:")
        print("=" * 60)
        print(result.stderr)
        print("=" * 60)
        
        cameras = []
        lines = result.stderr.split('\n')
        
        # 查找视频设备及其替代名称
        current_device = None
        for line in lines:
            line = line.strip()
            
            # 查找视频设备行
            if '(video)' in line and '"' in line:
                # 提取设备名称
                start = line.find('"')
                if start != -1:
                    end = line.find('"', start + 1)
                    if end != -1:
                        device_name = line[start + 1:end]
                        if '48MP USB Camera' in device_name:
                            current_device = {
                                'name': device_name,
                                'alternative_names': []
                            }
                            print(f"发现主设备: {device_name}")
            
            # 查找替代设备名称（通常在主设备行之后）
            elif current_device and 'Alternative name' in line:
                # 提取替代名称
                alt_match = re.search(r'Alternative name:\s*"([^"]+)"', line)
                if alt_match:
                    alt_name = alt_match.group(1)
                    current_device['alternative_names'].append(alt_name)
                    print(f"  替代名称: {alt_name}")
            
            # 如果遇到新的设备行，保存当前设备
            elif current_device and line and not line.startswith('  ') and '(video)' in line:
                cameras.append(current_device)
                current_device = None
        
        # 添加最后一个设备
        if current_device:
            cameras.append(current_device)
        
        return cameras
        
    except Exception as e:
        print(f"检测失败: {e}")
        return []

def test_directshow_devices():
    """测试DirectShow设备枚举"""
    try:
        # 使用Windows的DirectShow枚举工具
        import win32com.client
        
        print("\n使用DirectShow枚举设备:")
        print("=" * 40)
        
        # 创建系统设备枚举器
        system_device_enum = win32com.client.Dispatch("SystemDeviceEnum")
        
        # 创建视频输入设备类别
        video_input_category = system_device_enum.CreateClassEnumerator("CLSID_VideoInputDeviceCategory")
        
        device_count = 0
        while True:
            try:
                moniker = video_input_category.Next()
                if not moniker:
                    break
                
                # 获取属性包
                property_bag = moniker.BindToStorage(0, 0, "IPropertyBag")
                
                # 获取设备友好名称
                try:
                    friendly_name = property_bag.Read("FriendlyName", 0)
                    print(f"设备 {device_count}: {friendly_name}")
                    
                    # 获取设备路径
                    try:
                        device_path = property_bag.Read("DevicePath", 0)
                        print(f"  设备路径: {device_path}")
                    except:
                        pass
                    
                    device_count += 1
                except:
                    pass
                    
            except Exception as e:
                break
        
        print(f"\n共找到 {device_count} 个视频输入设备")
        
    except ImportError:
        print("需要安装 pywin32: pip install pywin32")
    except Exception as e:
        print(f"DirectShow枚举失败: {e}")

def main():
    """主函数"""
    print("=== 高级摄像头设备检测工具 ===")
    print(f"操作系统: {platform.system()}")
    print()
    
    # 获取FFmpeg设备信息
    cameras = get_detailed_camera_info()
    
    if cameras:
        print(f"\n找到 {len(cameras)} 个摄像头设备")
        for i, camera in enumerate(cameras):
            print(f"\n摄像头 {i+1}:")
            print(f"  主名称: {camera['name']}")
            if camera['alternative_names']:
                print(f"  替代名称:")
                for alt_name in camera['alternative_names']:
                    print(f"    - {alt_name}")
    
    # 尝试DirectShow枚举
    test_directshow_devices()

if __name__ == "__main__":
    main()