#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四路摄像头实时流式传输显示主程序
使用FFmpeg进行摄像头流式传输，PyQt构建UI界面
"""

import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# 先配置基本日志（在导入config之前）
if getattr(sys, 'frozen', False):
    _log_dir = os.path.dirname(sys.executable)
else:
    _log_dir = os.path.dirname(os.path.abspath(__file__))
_log_file = os.path.join(_log_dir, 'camera_stream.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(_log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if __package__:
    from .camera_stream import CameraStreamApp
else:
    from camera_stream import CameraStreamApp
if __package__:
    from .services.storage_service import StorageService
    from .config import config as app_config
else:
    from services.storage_service import StorageService
    from config import config as app_config

# 根据配置重新设置日志级别
_log_cfg = app_config.get_app_config('logging') or {}
_level_name = str((_log_cfg.get('level') or 'INFO')).upper()
_log_level = getattr(logging, _level_name, logging.INFO)
logger.setLevel(_log_level)
logging.getLogger().setLevel(_log_level)

def main():
    """主函数"""
    try:
        # 创建QApplication实例
        app = QApplication(sys.argv)
        app.setApplicationName("四路摄像头监控系统")
        app.setApplicationVersion("1.0.0")
        
        # 设置应用程序样式
        app.setStyle('Fusion')
        
        # 初始化存储服务与配置校验
        storage_service = StorageService()
        errors = app_config.validate_config()
        for err in errors:
            logger.warning(err)
        
        # 创建主窗口
        main_window = CameraStreamApp()
        main_window.show()
        
        logger.info("应用程序启动成功")
        
        # 运行应用程序
        return app.exec_()
        
    except Exception as e:
        logger.error(f"应用程序启动失败: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
