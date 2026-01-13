#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摄像头配置向导
帮助用户配置USB和IP摄像头
"""

import logging
from typing import Dict, List, Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QPushButton, QGroupBox, QGridLayout, 
    QMessageBox, QTextEdit, QTabWidget, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)

class CameraConfigWizard(QDialog):
    """摄像头配置向导"""
    config_saved = pyqtSignal(list)  # 发送新的摄像头配置列表
    
    def __init__(self, current_configs: List[Dict] = None):
        super().__init__()
        self.current_configs = current_configs or []
        self.new_configs = []
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("摄像头配置向导")
        self.setGeometry(200, 200, 800, 600)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("摄像头配置向导")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # USB摄像头配置页
        self.usb_tab = self._create_usb_config_tab()
        self.tab_widget.addTab(self.usb_tab, "USB摄像头")
        
        # IP摄像头配置页
        self.ip_tab = self._create_ip_config_tab()
        self.tab_widget.addTab(self.ip_tab, "IP摄像头")
        
        # 手动配置页
        self.manual_tab = self._create_manual_config_tab()
        self.tab_widget.addTab(self.manual_tab, "手动配置")
        
        main_layout.addWidget(self.tab_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("保存配置")
        self.save_button.clicked.connect(self.save_config)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self.test_connection)
        
        button_layout.addWidget(self.test_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                padding: 8px 16px;
                font-weight: bold;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
        """)
    
    def _create_usb_config_tab(self):
        """创建USB摄像头配置页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 说明文本
        info_label = QLabel("""
        USB摄像头配置说明：
        • 输入摄像头设备编号 (0, 1, 2, 3)
        • Windows系统通常使用 0, 1, 2, 3
        • Linux系统通常使用 /dev/video0, /dev/video1 等
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # USB摄像头配置组
        usb_group = QGroupBox("USB摄像头配置")
        usb_layout = QGridLayout()
        
        # 摄像头0
        usb_layout.addWidget(QLabel("摄像头 1:"), 0, 0)
        self.usb_camera_0 = QLineEdit("0")
        self.usb_camera_0.setPlaceholderText("输入设备编号，如: 0")
        usb_layout.addWidget(self.usb_camera_0, 0, 1)
        
        # 摄像头1
        usb_layout.addWidget(QLabel("摄像头 2:"), 1, 0)
        self.usb_camera_1 = QLineEdit("1")
        self.usb_camera_1.setPlaceholderText("输入设备编号，如: 1")
        usb_layout.addWidget(self.usb_camera_1, 1, 1)
        
        # 摄像头2
        usb_layout.addWidget(QLabel("摄像头 3:"), 2, 0)
        self.usb_camera_2 = QLineEdit("2")
        self.usb_camera_2.setPlaceholderText("输入设备编号，如: 2")
        usb_layout.addWidget(self.usb_camera_2, 2, 1)
        
        # 摄像头3
        usb_layout.addWidget(QLabel("摄像头 4:"), 3, 0)
        self.usb_camera_3 = QLineEdit("3")
        self.usb_camera_3.setPlaceholderText("输入设备编号，如: 3")
        usb_layout.addWidget(self.usb_camera_3, 3, 1)
        
        usb_group.setLayout(usb_layout)
        layout.addWidget(usb_group)
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab
    
    def _create_ip_config_tab(self):
        """创建IP摄像头配置页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 说明文本
        info_label = QLabel("""
        IP摄像头配置说明：
        • 输入RTSP流地址
        • 格式: rtsp://用户名:密码@IP地址:端口/路径
        • 示例: rtsp://admin:password@192.168.1.100:554/h264
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # IP摄像头配置组
        ip_group = QGroupBox("IP摄像头配置")
        ip_layout = QGridLayout()
        
        # 摄像头0
        ip_layout.addWidget(QLabel("摄像头 1:"), 0, 0)
        self.ip_camera_0 = QLineEdit()
        self.ip_camera_0.setPlaceholderText("rtsp://admin:password@192.168.1.100:554/h264")
        ip_layout.addWidget(self.ip_camera_0, 0, 1)
        
        # 摄像头1
        ip_layout.addWidget(QLabel("摄像头 2:"), 1, 0)
        self.ip_camera_1 = QLineEdit()
        self.ip_camera_1.setPlaceholderText("rtsp://admin:password@192.168.1.101:554/h264")
        ip_layout.addWidget(self.ip_camera_1, 1, 1)
        
        # 摄像头2
        ip_layout.addWidget(QLabel("摄像头 3:"), 2, 0)
        self.ip_camera_2 = QLineEdit()
        self.ip_camera_2.setPlaceholderText("rtsp://admin:password@192.168.1.102:554/h264")
        ip_layout.addWidget(self.ip_camera_2, 2, 1)
        
        # 摄像头3
        ip_layout.addWidget(QLabel("摄像头 4:"), 3, 0)
        self.ip_camera_3 = QLineEdit()
        self.ip_camera_3.setPlaceholderText("rtsp://admin:password@192.168.1.103:554/h264")
        ip_layout.addWidget(self.ip_camera_3, 3, 1)
        
        ip_group.setLayout(ip_layout)
        layout.addWidget(ip_group)
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab
    
    def _create_manual_config_tab(self):
        """创建手动配置页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 说明文本
        info_label = QLabel("""
        手动配置说明：
        • 直接编辑摄像头配置
        • 支持USB和IP摄像头
        • 可以设置分辨率、帧率等参数
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 手动配置文本框
        self.manual_config_text = QTextEdit()
        
        # 如果存在当前配置，显示它们
        if self.current_configs:
            import json
            config_text = json.dumps(self.current_configs, indent=2, ensure_ascii=False)
            self.manual_config_text.setPlainText(config_text)
        else:
            # 显示示例配置
            example_config = [
                {
                    "id": 0,
                    "name": "USB摄像头1",
                    "url": "0",
                    "enabled": True,
                    "resolution": "640x480",
                    "fps": 30
                },
                {
                    "id": 1,
                    "name": "USB摄像头2", 
                    "url": "1",
                    "enabled": True,
                    "resolution": "640x480",
                    "fps": 30
                }
            ]
            import json
            example_text = json.dumps(example_config, indent=2, ensure_ascii=False)
            self.manual_config_text.setPlainText(f"示例配置:\n{example_text}")
        
        layout.addWidget(self.manual_config_text)
        
        tab.setLayout(layout)
        return tab
    
    def save_config(self):
        """保存配置"""
        try:
            current_tab = self.tab_widget.currentIndex()
            
            if current_tab == 0:  # USB摄像头
                self._save_usb_config()
            elif current_tab == 1:  # IP摄像头
                self._save_ip_config()
            else:  # 手动配置
                self._save_manual_config()
            
            # 发送配置更新信号
            self.config_saved.emit(self.new_configs)
            
            QMessageBox.information(self, "成功", "配置已保存！")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
            logger.error(f"保存配置失败: {str(e)}")
    
    def _save_usb_config(self):
        """保存USB摄像头配置"""
        self.new_configs = []
        
        usb_configs = [
            (self.usb_camera_0.text().strip(), "USB摄像头1"),
            (self.usb_camera_1.text().strip(), "USB摄像头2"),
            (self.usb_camera_2.text().strip(), "USB摄像头3"),
            (self.usb_camera_3.text().strip(), "USB摄像头4"),
        ]
        
        for i, (url, name) in enumerate(usb_configs):
            if url:  # 只保存非空的配置
                config = {
                    "id": i,
                    "name": name,
                    "url": url,
                    "enabled": True,
                    "resolution": "640x480",
                    "fps": 30
                }
                self.new_configs.append(config)
    
    def _save_ip_config(self):
        """保存IP摄像头配置"""
        self.new_configs = []
        
        ip_configs = [
            (self.ip_camera_0.text().strip(), "IP摄像头1"),
            (self.ip_camera_1.text().strip(), "IP摄像头2"),
            (self.ip_camera_2.text().strip(), "IP摄像头3"),
            (self.ip_camera_3.text().strip(), "IP摄像头4"),
        ]
        
        for i, (url, name) in enumerate(ip_configs):
            if url:  # 只保存非空的配置
                config = {
                    "id": i,
                    "name": name,
                    "url": url,
                    "enabled": True,
                    "resolution": "640x480",
                    "fps": 30
                }
                self.new_configs.append(config)
    
    def _save_manual_config(self):
        """保存手动配置"""
        try:
            import json
            config_text = self.manual_config_text.toPlainText().strip()
            
            # 如果包含示例文本，只提取JSON部分
            if "示例配置:" in config_text:
                config_text = config_text.split("示例配置:")[1].strip()
            
            self.new_configs = json.loads(config_text)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON格式错误: {str(e)}")
    
    def test_connection(self):
        """测试摄像头连接"""
        try:
            current_tab = self.tab_widget.currentIndex()
            
            if current_tab == 0:  # USB摄像头
                test_urls = [self.usb_camera_0.text().strip()]
            elif current_tab == 1:  # IP摄像头
                test_urls = [self.ip_camera_0.text().strip()]
            else:
                QMessageBox.information(self, "提示", "请在USB或IP摄像头页面进行测试")
                return
            
            # 简单的URL格式验证
            for url in test_urls:
                if not url:
                    QMessageBox.warning(self, "警告", "请先输入摄像头地址")
                    return
                
                if current_tab == 1 and not url.startswith(('rtsp://', 'rtmp://', 'http://')):
                    QMessageBox.warning(self, "警告", "IP摄像头地址格式不正确")
                    return
            
            QMessageBox.information(self, "测试", "连接测试功能需要实际运行环境验证")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"测试失败: {str(e)}")
            logger.error(f"测试连接失败: {str(e)}")


def show_camera_config_wizard(parent=None, current_configs: List[Dict] = None):
    """显示摄像头配置向导"""
    wizard = CameraConfigWizard(current_configs)
    wizard.setWindowFlags(wizard.windowFlags() | Qt.WindowStaysOnTopHint)
    
    if wizard.exec_() == QDialog.Accepted:
        return wizard.new_configs
    return None