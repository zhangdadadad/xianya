#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件模块
包含摄像头配置、网络设置等
"""

import os
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class Config:
    """配置管理类"""
    
    # 默认摄像头配置 - 支持USB摄像头
    DEFAULT_CAMERA_CONFIGS = [
        {
            "id": 0,
            "name": "USB摄像头1",
            "url": "0",
            "enabled": True,
            "resolution": "640x480",
            "fps": 30,
            "type": "usb"
        },
        {
            "id": 1,
            "name": "USB摄像头2",
            "url": "1",
            "enabled": True,
            "resolution": "640x480",
            "fps": 30,
            "type": "usb"
        },
        {
            "id": 2,
            "name": "USB摄像头3",
            "url": "2",
            "enabled": True,
            "resolution": "640x480",
            "fps": 30,
            "type": "usb"
        },
        {
            "id": 3,
            "name": "USB摄像头4",
            "url": "3",
            "enabled": True,
            "resolution": "640x480",
            "fps": 30,
            "type": "usb"
        }
    ]
    
    # 默认应用配置
    DEFAULT_APP_CONFIG = {
        "window": {
            "title": "湘雅面诊实时采集系统",
            "width": 1400,
            "height": 900,
            "x": 100,
            "y": 100
        },
        "video": {
            "buffer_size": 30,
            "reconnect_interval": 5,
            "timeout": 10,
            "prefer_opencv_for_numeric": True
        },
        "logging": {
            "level": "INFO",
            "file": "camera_stream.log",
            "max_size": 10 * 1024 * 1024,  # 10MB
            "backup_count": 5
        },
        "analysis": {
            "cooldown_sec": 2.0,
            "min_face": 64,
            "trigger_frames": 6,
            "detector": "haar"  # 可选: haar|yunet
        },
        "capture": {
            "enable": True,
            "dir": "captures",
            "count_per_camera": 3
        },
        "ffmpeg": {
            "timeout": 30,
            "reconnect_attempts": 3,
            "low_latency": True,
            "custom_path": r"c:\\Users\\Administrator\\Documents\\trae_projects\\opencv\\camera\\ffmpeg-7.1.1-essentials_build\\bin\\ffmpeg.exe"  # 自定义FFmpeg路径
        }
    }
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.camera_configs = self.DEFAULT_CAMERA_CONFIGS.copy()
        self.app_config = self.DEFAULT_APP_CONFIG.copy()
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 加载摄像头配置
                if 'cameras' in config_data:
                    self.camera_configs = config_data['cameras']
                
                # 加载应用配置
                if 'app' in config_data:
                    self._deep_update(self.app_config, config_data['app'])
                
                logger.info(f"配置文件加载成功: {self.config_file}")
            else:
                logger.info("使用默认配置")
                self.save_config()
                
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            logger.info("使用默认配置")
    
    def save_config(self):
        """保存配置文件"""
        try:
            config_data = {
                'cameras': self.camera_configs,
                'app': self.app_config
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置文件保存成功: {self.config_file}")
            
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
    
    def get_camera_config(self, camera_id: int) -> Dict[str, Any]:
        """获取摄像头配置"""
        for config in self.camera_configs:
            if config['id'] == camera_id:
                return config.copy()
        return {}
    
    def update_camera_config(self, camera_id: int, config: Dict[str, Any]):
        """更新摄像头配置"""
        for i, camera_config in enumerate(self.camera_configs):
            if camera_config['id'] == camera_id:
                self.camera_configs[i] = config
                self.save_config()
                logger.info(f"摄像头 {camera_id} 配置已更新")
                return
        
        # 如果找不到现有配置，添加新配置
        self.camera_configs.append(config)
        self.save_config()
        logger.info(f"摄像头 {camera_id} 配置已添加")
    
    def get_camera_configs(self) -> List[Dict[str, Any]]:
        """获取摄像头配置"""
        return self.camera_configs.copy()
    
    def get_app_config(self, key: str = None) -> Any:
        """获取应用配置"""
        if key is None:
            return self.app_config.copy()
        
        keys = key.split('.')
        value = self.app_config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        return value
    
    def update_app_config(self, key: str, value: Any):
        """更新应用配置"""
        keys = key.split('.')
        config = self.app_config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self.save_config()
        logger.info(f"应用配置 {key} 已更新")
    
    def get_enabled_cameras(self) -> List[Dict[str, Any]]:
        """获取启用的摄像头配置"""
        return [config for config in self.camera_configs if config.get('enabled', True)]
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """深度更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def validate_config(self) -> List[str]:
        """验证配置有效性"""
        errors = []
        
        # 验证摄像头配置
        for i, config in enumerate(self.camera_configs):
            if not isinstance(config, dict):
                errors.append(f"摄像头配置 {i} 不是有效的字典")
                continue
            
            required_fields = ['id', 'url']
            for field in required_fields:
                if field not in config:
                    errors.append(f"摄像头配置 {i} 缺少必要字段: {field}")
            
            if 'id' in config and not isinstance(config['id'], int):
                errors.append(f"摄像头配置 {i} 的ID必须是整数")
            
            if 'url' in config and not config['url']:
                errors.append(f"摄像头配置 {i} 的URL不能为空")
        
        # 验证应用配置
        if not isinstance(self.app_config, dict):
            errors.append("应用配置不是有效的字典")
        
        return errors


# 全局配置实例
config = Config()
