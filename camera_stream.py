#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt主界面模块
负责创建四路摄像头显示界面
"""

import sys
import logging
import numpy as np
import cv2
import time
import threading
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import asyncio
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QGridLayout, QGroupBox,
    QTextEdit, QSplitter, QStatusBar, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap, QPalette, QColor

try:
    from .ffmpeg_stream import CameraManager, FFMPEG_AVAILABLE
except Exception:
    from ffmpeg_stream import CameraManager, FFMPEG_AVAILABLE
try:
    from .services.analysis_service import AnalysisService, FaceBox
    from .services.storage_service import StorageService
except Exception:
    from services.analysis_service import AnalysisService, FaceBox
    from services.storage_service import StorageService
try:
    from .services.trigger_service import TriggerService, KeyboardTriggerProvider
except Exception:
    from services.trigger_service import TriggerService, KeyboardTriggerProvider
try:
    from .services.guidance_service import GuidanceService
except Exception:
    from services.guidance_service import GuidanceService



logger = logging.getLogger(__name__)

class VideoLabel(QLabel):
    """自定义视频标签"""
    def __init__(self, camera_id: int):
        super().__init__()
        self.camera_id = camera_id
        self.setMinimumSize(320, 240)
        self.setScaledContents(True)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #ccc;
                background-color: #000;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setText(f"摄像头 {camera_id + 1}\n等待连接...")
    
    def update_frame(self, frame: np.ndarray):
        """更新视频帧"""
        try:
            # FFmpeg返回的是RGB格式，直接使用
            # 复制数据，确保QImage不会引用临时数据
            frame_rgb = frame.copy()
            
            # 转换numpy数组为QImage
            height, width, channel = frame_rgb.shape
            bytes_per_line = channel * width
            
            q_image = QImage(
                frame_rgb.data, width, height, bytes_per_line, 
                QImage.Format_RGB888
            )
            
            # 转换为QPixmap并显示
            pixmap = QPixmap.fromImage(q_image)
            self.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"更新摄像头 {self.camera_id} 帧失败: {str(e)}")
            self.setText(f"摄像头 {self.camera_id + 1}\n显示错误")
    def show_standby(self):
        try:
            self.setPixmap(QPixmap())
        except Exception:
            pass
        self.setText(f"摄像头 {self.camera_id + 1}\n待机中...")


class CameraStreamApp(QMainWindow):
    """主应用程序窗口"""
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.camera_manager = CameraManager()
        self.video_labels = {}
        self.update_timers = {}
        self.detections = {}
        self.capture_in_progress = False
        self.waiting_for_trigger = False
        self.armed_for_capture = False
        self.qr_code_scanned = False  # 标记是否已扫描到二维码（由扫码盒控制）
        self.locked_box = None
        self.prompt_text = ""
        self.pending_payload = None
        self.current_trigger_code = None
        # 配置读取函数
        try:
            from config import config as app_config
            self._cfg_get = lambda k: app_config.get_app_config(k)
        except Exception:
            self._cfg_get = lambda k: None
        # 初始化分析与存储服务
        self.analysis_service = AnalysisService(self._cfg_get)
        self.storage_service = StorageService()
        self.guidance_service = GuidanceService(lambda: (self.last_frames.get(0), self.detections.get(0) or []))
        
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        """初始化UI界面"""
        title = self._cfg_get('window.title') or "四路摄像头实时监控系统"
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        self.video_group = QGroupBox("视频显示")
        self.video_layout = QGridLayout(self.video_group)
        
        positions = self._get_positions()
        for i in range(4):
            video_label = VideoLabel(i)
            self.video_labels[i] = video_label
            row, col = positions.get(i, (i // 2, i % 2))
            self.video_layout.addWidget(video_label, row, col)
        
        # 创建右侧控制面板
        control_group = QGroupBox("控制面板")
        control_layout = QVBoxLayout(control_group)
        
        # 添加控制按钮
        self.start_button = QPushButton("开始监控")
        self.stop_button = QPushButton("停止监控")
        self.stop_button.setEnabled(False)
        
        # 禁用按钮的空格键默认行为
        self.start_button.setFocusPolicy(Qt.NoFocus)
        self.stop_button.setFocusPolicy(Qt.NoFocus)
        
        self.ffmpeg_status_label = QLabel()
        
        # 添加日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        
        # 添加FFmpeg状态提示
        if not FFMPEG_AVAILABLE:
            self.ffmpeg_status_label.setText("⚠️ FFmpeg未安装，使用测试模式")
            self.ffmpeg_status_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.ffmpeg_status_label.setText("✓ FFmpeg已安装")
            self.ffmpeg_status_label.setStyleSheet("color: green; font-weight: bold;")
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.ffmpeg_status_label)
        control_layout.addWidget(QLabel("运行日志:"))
        control_layout.addWidget(self.log_text)
        control_layout.addStretch()
        
        # 添加到主布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.video_group)
        splitter.addWidget(control_group)
        splitter.setSizes([1000, 400])
        
        main_layout.addWidget(splitter)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("准备就绪")
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-size: 14px;
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
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 3px;
            }
        """)
        
    def connect_signals(self):
        """连接信号和槽"""
        self.start_button.clicked.connect(self.start_monitoring)
        self.stop_button.clicked.connect(self.stop_monitoring)
        #self.config_button.clicked.connect(self.open_config_wizard)
        
        # 连接摄像头管理器信号
        self.camera_manager.frame_updated.connect(self.update_video_frame)
        self.camera_manager.error_occurred.connect(self.show_error)
        # 分析服务信号与订阅
        self.camera_manager.frame_updated.connect(self.analysis_service.on_frame)
        self.analysis_service.result_ready.connect(self.on_analysis_result)
        self.analysis_service.capture_suggested.connect(self.on_capture_suggested)
        # UI信号（主线程更新）
        self.log_signal.connect(self._append_log)
        self.status_signal.connect(self.status_bar.showMessage)
        self.last_frames = {}
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self.render_tick)
        self.render_timer.start(33)
        

        
        # 初始化触发服务
        self.trigger_service = TriggerService()
        self.trigger_service.set_provider(KeyboardTriggerProvider())
        self.trigger_service.triggered.connect(self.on_capture_trigger)
        self.trigger_service.identified.connect(self.on_capture_identified)
        
        # 初始化二维码扫描服务
      
        
    def start_monitoring(self):
        """开始监控"""
        try:
            self.log_message("正在启动摄像头监控...")
            self.status_bar.showMessage("正在连接摄像头...")
            
            # 只启动主摄像头 (ID=0)
            self.camera_manager.start_camera(0)
            # 更新UI状态
            for i, label in self.video_labels.items():
                if i == 0:
                    label.setText(f"摄像头 {i + 1}\n正在监控...")
                else:
                    label.setText(f"摄像头 {i + 1}\n待机中...")
            
            # 信号驱动，无需轮询定时器
            
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_bar.showMessage("监控运行中")
            self.log_message("摄像头监控已启动")
            
            # 启动键盘触发服务
            try:
                self.trigger_service.start()
            except Exception as e:
                self.log_message(f"启动键盘触发服务失败: {e}")
            
        except Exception as e:
            error_msg = f"启动监控失败: {str(e)}"
            self.log_message(error_msg)
            self.show_error(error_msg)
    
    def stop_monitoring(self):
        """停止监控"""
        try:
            self.log_message("正在停止摄像头监控...")
            self.status_bar.showMessage("正在断开摄像头连接...")
            
            # 无轮询定时器，无需停止
            
            # 停止所有摄像头
            self.camera_manager.stop_all_cameras()
            
            # 重置视频标签
            for i, label in self.video_labels.items():
                if i == 0:
                    label.setText(f"摄像头 {i + 1}\n待机中...")
                else:
                    label.setText(f"摄像头 {i + 1}\n等待连接...")
            
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.status_bar.showMessage("监控已停止")
            self.log_message("摄像头监控已停止")
            
        except Exception as e:
            error_msg = f"停止监控失败: {str(e)}"
            self.log_message(error_msg)
            self.show_error(error_msg)
    
    def update_camera_display(self, camera_id: int):
        """保留接口（不使用轮询）"""
        try:
            pass
        except Exception:
            pass
    
    def update_video_frame(self, stream_id: int, frame: np.ndarray):
        """更新视频帧（由摄像头管理器调用）"""
        try:
            self.last_frames[stream_id] = frame
        except Exception as e:
            logger.error(f"更新视频帧失败: {str(e)}")

    def on_analysis_result(self, stream_id: int, boxes: list):
        try:
            self.detections[stream_id] = boxes
        except Exception:
            pass

    def _on_frame_for_qr_scan(self, stream_id: int, frame: np.ndarray):
        """在帧上进行二维码扫描 - 优化版本"""
        if stream_id == 0:  # 只在主摄像头进行二维码扫描
            current_time = time.time() * 1000  # 转换为毫秒
            if current_time - self.last_qr_scan_time >= self.qr_scan_interval:
                self.last_qr_scan_time = current_time
                # 创建帧的深拷贝以避免多线程数据共享问题
                frame_copy = frame.copy()
                # 使用线程池执行二维码扫描，减少线程创建开销
                self._qr_scan_pool.submit(lambda: self.qr_scanner.scan_qr_code(frame_copy, stream_id))
    
    def on_qr_code_detected(self, qr_data: str):
        """处理二维码检测事件"""
        try:
            self.log_message(f"检测到二维码: {qr_data}")
            self.current_trigger_code = qr_data
            self.qr_code_scanned = True  # 标记已扫描到二维码
            
            # 二维码检测后，显示提示，等待按空格键开始
            self.armed_for_capture = False
            self.prompt_text = "二维码已识别，请按空格键开始拍照"
            self.status_signal.emit(self.prompt_text)
        except Exception as e:
            self.log_message(f"处理二维码事件失败: {e}")

    def on_capture_suggested(self, stream_id: int, payload: object):
        if stream_id != 0:
            return
        try:
            main_frame, best_box = payload
            self.locked_box = best_box
            self.pending_payload = (main_frame, best_box)
            if self.capture_in_progress:
                return
            # 直接开始拍照
            self.capture_in_progress = True
            self.prompt_text = "请保持不动，正在采集中..."
            self.status_signal.emit("正在联动采集...")
            try:
                self.guidance_service.hold()
                self.guidance_service.stop()
            except Exception:
                pass
            threading.Thread(target=self._capture_all, args=((main_frame, best_box),), daemon=True).start()
        except Exception as e:
            self.log_message(f"启动抓拍准备失败: {e}")
    def on_capture_trigger(self, code: str):
        try:
            if self.capture_in_progress:
                return
            # 只有检测到二维码后，按空格键才能拍照
            if not self.qr_code_scanned:
                self.log_message("请先扫描二维码")
                return
            
            # 按空格键后，直接开始拍照
            self.capture_in_progress = True
            self.qr_code_scanned = False  # 重置二维码标记
            self.prompt_text = "正在拍照..."
            self.status_signal.emit("正在拍照...")
            
            # 获取主摄像头的当前帧
            main_frame = self.last_frames.get(0)
            if main_frame is None:
                self.log_message("无法获取主摄像头帧")
                self.capture_in_progress = False
                return
            
            # 获取检测到的人脸框（如果有）
            detections = self.detections.get(0) or []
            best_box = None
            if detections:
                best_box = detections[0]
            
            # 直接开始拍照
            threading.Thread(target=self._capture_all, args=((main_frame, best_box),), daemon=True).start()
            
        except Exception as e:
            self.log_message(f"触发采集失败: {e}")
            self.capture_in_progress = False
    def on_capture_identified(self, code: str):
        try:
            self.current_trigger_code = code
            self.qr_code_scanned = True  # 扫码盒扫码后设置为True
            self.log_message(f"扫码成功: {code}")
            self.status_signal.emit("扫码成功，请按空格键拍照")
        except Exception as e:
            self.log_message(f"处理扫码数据失败: {e}")
    


    def _capture_all(self, payload: object):
        """执行所有摄像头的抓拍和保存"""
        try:
            main_frame, best_box = payload
            self.log_message("开始联动抓拍...")
            
            # 确保 best_box 不为 None
            if best_box is None:
                # 创建一个默认的人脸框（居中）
                h, w = main_frame.shape[:2]
                from services.analysis_service import FaceBox
                best_box = FaceBox(w // 4, h // 4, w // 2, h // 2, 0.0)
            
            # 1. 保存主摄像头的帧并提示成功
            frames_to_save = {}
            try:
                # 为确保每次扫码创建新文件夹，在session_id后添加时间戳
                if self.current_trigger_code:
                    session_id = f"{str(self.current_trigger_code)}_{time.strftime('%Y%m%d%H%M%S')}"
                else:
                    session_id = time.strftime('%Y%m%d%H%M%S')
            except Exception:
                session_id = time.strftime('%Y%m%d%H%M%S')
            try:
                camera_name = "cam1"
                bbox = (best_box.x, best_box.y, best_box.w, best_box.h)
                det_score = best_box.score
                pid = None
                try:
                    if isinstance(self.current_trigger_code, str) and self.current_trigger_code.isdigit():
                        pid = int(self.current_trigger_code)
                except Exception:
                    pass
                count = int(self._cfg_get('capture.count_per_camera') or 1)
                frames_list = []
                # 为确保获取新帧，使用更高效的方式
                for i in range(max(1, count)):
                    # 使用缓存的最新帧
                    f = self.last_frames.get(0)
                    if f is not None:
                        frames_list.append(f.copy())
                    else:  # 如果获取失败，使用main_frame
                        frames_list.append(main_frame)
                    
                    # 如果需要多帧，等待一小段时间
                    if i < count - 1:
                        time.sleep(0.05)  # 减少延迟，降低CPU占用
                
                # 确保至少有一帧
                if not frames_list:
                    frames_list = [main_frame]
                    
                frames_to_save[0] = frames_list
                self.log_message(f"主摄像头已抓取 {len(frames_list)} 帧")
                self.prompt_text = "主摄像头捕捉成功，抓拍其它相机..."
                self.status_signal.emit("主摄像头捕捉成功，抓拍其它相机...")
            except Exception as e:
                self.log_message(f"保存主摄像头图像失败: {e}")
            
            # 2. 依次尝试抓拍其他摄像头，但只保存成功获取图像的摄像头
            other_camer_ids = [1, 2, 3]
            # 暂停主摄像头释放设备占用
            try:
                self.camera_manager.stop_camera(0)
            except Exception:
                pass
            for cam_id in other_camer_ids:
                try:
                    self.log_message(f"尝试启动摄像头 {cam_id + 1}...")
                    self.video_labels[cam_id].setText(f"摄像头 {cam_id + 1}\n正在尝试抓拍...")
                    self.camera_manager.start_camera(cam_id)
                    t0 = time.time()
                    frame = None
                    # 尝试获取图像
                    while time.time() - t0 < 2.5:
                        f = self.camera_manager.get_frame(cam_id)
                        if f is not None:
                            frame = f
                            break
                        time.sleep(0.05)
                    
                    # 只有成功获取到图像才保存
                    if frame is not None:
                        count = int(self._cfg_get('capture.count_per_camera') or 1)
                        frames = []
                        # 为确保获取新帧，不使用缓存帧
                        for j in range(max(1, count)):
                            f2 = None
                            t1 = time.time()
                            while time.time() - t1 < 0.5:
                                # 直接从摄像头管理器获取最新帧
                                g2 = self.last_frames.get(cam_id)
                                if g2 is not None:
                                    # 创建帧的深拷贝以避免后续处理影响
                                    f2 = g2.copy()
                                    # 小延迟确保获取不同时间点的帧
                                    time.sleep(0.05)
                                    break
                                time.sleep(0.03)
                            if f2 is not None:
                                frames.append(f2)
                            elif j == 0:  # 如果第一帧就失败，使用frame
                                frames.append(frame)
                            else:  # 否则使用已获取的最新帧的拷贝
                                frames.append(frames[-1].copy())
                        
                        # 确保至少有一帧
                        if not frames:
                            frames = [frame]
                            
                        frames_to_save[cam_id] = frames
                        self.log_message(f"摄像头 {cam_id + 1} 抓拍成功，共 {len(frames)} 帧")
                    else:
                        self.log_message(f"摄像头 {cam_id + 1} 未连接或未能获取到图像，跳过保存")
                        # 不保存未连接摄像头的照片
                except Exception as e:
                    self.log_message(f"获取摄像头 {cam_id + 1} 图像失败: {e}")
                    # 不保存出错摄像头的照片
                finally:
                    try:
                        self.camera_manager.stop_camera(cam_id)
                        self.camera_manager.last_frames[cam_id] = None
                        self.last_frames[cam_id] = None
                        self.detections[cam_id] = []
                        self.video_labels[cam_id].show_standby()
                    except Exception as e:
                        self.log_message(f"停止摄像头 {cam_id + 1} 失败: {e}")
            # 恢复主摄像头
            try:
                self.camera_manager.start_camera(0)
                self.video_labels[0].setText(f"摄像头 1\n正在监控...")
            except Exception:
                pass

            # 6. 保存所有抓拍到的图像
            saved_files = []
            session_id = None
            try:
                # 为确保每次扫码创建新文件夹，在session_id后添加时间戳
                if self.current_trigger_code:
                    session_id = f"{str(self.current_trigger_code)}_{time.strftime('%Y%m%d%H%M%S')}"
                else:
                    session_id = time.strftime('%Y%m%d%H%M%S')
            except Exception:
                session_id = time.strftime('%Y%m%d%H%M%S')
            for cam_id, frames in frames_to_save.items():
                try:
                    camera_name = f"cam{cam_id + 1}"
                    bbox = (best_box.x, best_box.y, best_box.w, best_box.h) if cam_id == 0 else None
                    det_score = best_box.score if cam_id == 0 else None
                    pid = None
                    try:
                        if isinstance(self.current_trigger_code, str) and self.current_trigger_code.isdigit():
                            pid = int(self.current_trigger_code)
                    except Exception:
                        pass
                    for frame in frames:
                        rel_path = self.storage_service.save_capture(
                            camera_name=camera_name,
                            frame=frame,
                            bbox=bbox,
                            det_score=det_score,
                            person_id=pid,
                            rec_score=None,
                            session_id=session_id,
                        )
                        saved_files.append(rel_path)
                except Exception as e:
                    self.log_message(f"保存摄像头 {cam_id + 1} 图像失败: {e}")
            
            if saved_files:
                self.log_message(f"联动抓拍完成，共保存 {len(saved_files)} 张图像: {', '.join(saved_files)}")
                self.status_signal.emit("身份认证成功")
                self.log_message("身份认证成功")
            else:
                self.log_message("联动抓拍失败，未能保存任何图像")
            for cid in [1, 2, 3]:
                try:
                    self.camera_manager.last_frames[cid] = None
                    self.last_frames[cid] = None
                    self.detections[cid] = []
                    self.video_labels[cid].show_standby()
                except Exception:
                    pass
            self.capture_in_progress = False
            self.waiting_for_trigger = False
            self.armed_for_capture = False
            self.locked_box = None
            self.prompt_text = "采集结束"
            self.pending_payload = None
            self.current_trigger_code = None
            try:
                self.guidance_service.stop()
            except Exception:
                pass

        except Exception as e:
            self.log_message(f"联动抓拍失败: {e}")

    def render_tick(self):
        try:
            for i in range(4):
                f = self.last_frames.get(i)
                if f is None:
                    continue
                overlay = f.copy()
                try:
                    if i == 0:
                        h, w = overlay.shape[0], overlay.shape[1]
                        x0 = int(w * 0.35)
                        y0 = int(h * 0.35)
                        x1 = int(w * 0.65)
                        y1 = int(h * 0.65)
                        cv2.rectangle(overlay, (x0, y0), (x1, y1), (255, 255, 0), 1)
                        
                        # 显示二维码检测结果
                        if hasattr(self, 'qr_scanner') and self.qr_scanner.last_scan_info:
                            qr_info = self.qr_scanner.last_scan_info
                            if qr_info['detected']:
                                # 绘制二维码边界框
                                if qr_info['polygon']:
                                    pts = np.array(qr_info['polygon'], dtype=np.int32).reshape((-1, 1, 2))
                                    cv2.polylines(overlay, [pts], True, (0, 0, 255), 2)
                                # 显示二维码内容
                                cv2.putText(overlay, f"QR: {qr_info['data']}", (20, 80), 
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        
                        if (self.capture_in_progress or self.waiting_for_trigger) and self.locked_box is not None:
                            b = self.locked_box
                            cv2.rectangle(overlay, (b.x, b.y), (b.x + b.w, b.y + b.h), (0, 255, 255), 2)
                            if self.prompt_text:
                                cv2.putText(overlay, self.prompt_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
                            self.video_labels[i].update_frame(overlay)
                            continue
                    boxes = self.detections.get(i) or []
                    if boxes:
                        for b in boxes:
                            cv2.rectangle(overlay, (b.x, b.y), (b.x + b.w, b.y + b.h), (0, 255, 0), 2)
                            cv2.putText(overlay, f"{b.score:.2f}", (b.x, b.y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                except Exception:
                    pass
                self.video_labels[i].update_frame(overlay)
        except Exception:
            pass
    
    def show_error(self, error_msg: str):
        """显示错误消息"""
        # 改进错误消息显示
        if "WinError 2" in error_msg or "找不到指定的文件" in error_msg:
            error_msg = f"""{error_msg}

可能的原因和解决方案：
1. FFmpeg未安装 - 请先安装FFmpeg
2. 系统会自动切换到测试模式
3. 请检查摄像头设备是否正确连接"""
        
        QMessageBox.critical(self, "错误", error_msg)
        self.log_message(f"错误: {error_msg}")
    
    def log_message(self, message: str):
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(f"[DEBUG] {log_entry}")  # 添加调试输出
        try:
            logger.info(log_entry)
        except Exception:
            pass
        try:
            self.log_signal.emit(log_entry)
        except Exception as e:
            print(f"[ERROR] Failed to emit log signal: {e}")

    def _append_log(self, log_entry: str):
        self.log_text.append(log_entry)
        try:
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
        except Exception as e:
            print(f"[ERROR] Failed to scroll log: {e}")
    
    def _get_positions(self):
        positions = {}
        try:
            configs = getattr(self.camera_manager, 'camera_configs', [])
            for cfg in configs:
                i = cfg.get('id')
                r = cfg.get('grid_row')
                c = cfg.get('grid_col')
                if isinstance(i, int) and isinstance(r, int) and isinstance(c, int):
                    positions[i] = (r, c)
        except Exception:
            pass
        return positions

    def _apply_positions(self):
        try:
            positions = self._get_positions()
            for i in range(4):
                label = self.video_labels.get(i)
                if not label:
                    continue
                row, col = positions.get(i, (i // 2, i % 2))
                self.video_layout.addWidget(label, row, col)
        except Exception:
            pass
        
    
    def closeEvent(self, event):
        """关闭事件处理"""
        try:
            try:
                self.trigger_service.stop()
            except Exception:
                pass
            self.stop_monitoring()
            event.accept()
        except Exception as e:
            logger.error(f"关闭应用程序时出错: {str(e)}")
            event.accept()