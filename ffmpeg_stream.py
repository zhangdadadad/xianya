#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFmpeg摄像头流式传输核心模块
负责处理摄像头连接、流式传输和图像处理
"""

import subprocess
import threading
import queue
import time
import logging
import numpy as np
import platform
import os
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap

# 初始化logger
logger = logging.getLogger(__name__)

def check_ffmpeg_available():
    """检查FFmpeg是否可用 - 支持自定义路径"""
    try:
        # 从配置文件获取自定义路径
        try:
            from .config import config
        except Exception:
            from config import config
        custom_path = config.get_app_config('ffmpeg.custom_path')
        
        # 添加当前项目中的FFmpeg路径
        project_ffmpeg_path = r"c:\Users\Administrator\Documents\trae_projects\opencv\camera\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
        
        # 自定义FFmpeg路径列表（包含配置文件中的路径）
        custom_paths = [project_ffmpeg_path]  # 直接添加项目中的FFmpeg路径
        
        if custom_path:
            custom_paths.append(custom_path)
            
        # 添加其他常见路径
        custom_paths.extend([
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        ])
        
        logger.info(f"尝试的FFmpeg路径列表: {custom_paths}")
        
        # 首先尝试自定义路径
        for ffmpeg_path in custom_paths:
            logger.info(f"检查FFmpeg路径: {ffmpeg_path}")
            if os.path.exists(ffmpeg_path):
                logger.info(f"FFmpeg文件存在: {ffmpeg_path}")
                try:
                    result = subprocess.run([ffmpeg_path, '-version'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        # 设置全局变量供后续使用
                        global FFMPEG_PATH
                        FFMPEG_PATH = ffmpeg_path
                        logger.info(f"找到并成功测试FFmpeg: {ffmpeg_path}")
                        return True
                    else:
                        logger.warning(f"FFmpeg返回非零退出码: {result.returncode}")
                except Exception as e:
                    logger.error(f"运行FFmpeg时出错: {e}")
                    continue
        
        # 尝试系统PATH
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                FFMPEG_PATH = 'ffmpeg'  # 使用系统PATH中的ffmpeg
                logger.info("找到FFmpeg (系统PATH)")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.error(f"系统PATH中找不到FFmpeg: {e}")
        
        logger.warning("未找到可用的FFmpeg")
        return False
        
    except Exception as e:
        logger.error(f"FFmpeg检测失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# FFmpeg可用性检查
FFMPEG_AVAILABLE = check_ffmpeg_available()

class TestStream(QObject):
    """测试流 - 当FFmpeg不可用时生成测试图像"""
    frame_received = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, camera_id: int, resolution=(480, 640, 3)):
        super().__init__()
        self.camera_id = camera_id
        self.is_running = False
        self.resolution = resolution
        self.thread = None
        self.frame_count = 0
        
    def start_stream(self):
        """开始测试流"""
        self.is_running = True
        self.thread = threading.Thread(target=self._generate_frames)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"测试摄像头 {self.camera_id} 已启动")
    
    def _generate_frames(self):
        """生成测试帧"""
        import cv2
        from datetime import datetime
        
        while self.is_running:
            try:
                # 创建测试图像
                frame = np.zeros(self.resolution, dtype=np.uint8)
                
                # 添加摄像头编号
                cv2.putText(frame, f"USB Camera {self.camera_id}", 
                           (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                           1, (255, 255, 255), 2)
                
                # 添加时间戳
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, timestamp, 
                           (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.5, (255, 255, 255), 1)
                
                # 添加帧计数
                cv2.putText(frame, f"Frame: {self.frame_count}", 
                           (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.5, (255, 255, 255), 1)
                
                # 添加动态内容
                if self.frame_count % 30 < 15:
                    cv2.circle(frame, (320, 240), 50, (0, 255, 0), -1)
                else:
                    cv2.circle(frame, (320, 240), 50, (0, 0, 255), -1)
                
                self.frame_count += 1
                
                # 发送帧
                self.frame_received.emit(frame)
                
                # 控制帧率 (30fps)
                time.sleep(1/30)
                
            except Exception as e:
                logger.error(f"测试帧生成失败: {str(e)}")
                self.error_occurred.emit(f"测试摄像头 {self.camera_id} 帧生成失败: {str(e)}")
                break
    
    def stop_stream(self):
        """停止测试流"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1)
        logger.info(f"测试摄像头 {self.camera_id} 已停止")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """获取当前帧"""
        return None  # 测试流通过信号发送帧

class FFmpegStream(QObject):
    """FFmpeg流式传输类 - 支持USB摄像头和IP摄像头"""
    frame_received = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, camera_url: str, stream_id: int):
        super().__init__()
        self.camera_url = camera_url
        self.stream_id = stream_id
        self.process = None
        self.is_running = False
        self.is_starting = False
        self.frame_queue = queue.Queue(maxsize=30)
        self.thread = None
        self.is_usb_camera = self._is_usb_camera()
        self.fallback_attempted = False
        self.pending_restart = False
        self.restart_attempts = 0
        self.on_frame_callback = None
        self.frame_count = 0
        self.publish_stride = 1
        self.last_frame_at = 0.0
    
    def _is_usb_camera(self) -> bool:
        """判断是否为USB摄像头"""
        return (self.camera_url.startswith('/dev/video') or 
                self.camera_url.startswith('video=') or
                self.camera_url.startswith('@device_pnp_') or
                self.camera_url.startswith('0') or
                self.camera_url.startswith('1') or
                self.camera_url.startswith('2') or
                self.camera_url.startswith('3'))
        
    def start_stream(self):
        """开始流式传输"""
        try:
            if self.is_starting or self.is_running:
                return
            self.is_starting = True
            # 检查FFmpeg是否可用
            if not FFMPEG_AVAILABLE:
                error_msg = "FFmpeg未安装，使用测试模式"
                logger.warning(error_msg)
                self.error_occurred.emit(error_msg)
                self._start_test_mode()
                self.is_starting = False
                return
            
            # 根据摄像头类型选择不同的FFmpeg参数
            if self.is_usb_camera:
                cmd = self._get_usb_camera_cmd()
            else:
                cmd = self._get_ip_camera_cmd()
            
            logger.info(f"启动摄像头 {self.stream_id}: {self.camera_url}")
            logger.info(f"FFmpeg命令: {' '.join(cmd)}")
            
            # 启动FFmpeg进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )
            
            self.is_running = True
            self.is_starting = False
            
            # 启动帧读取线程
            self.thread = threading.Thread(target=self._read_frames)
            self.thread.daemon = True
            self.thread.start()

            # 启动错误输出读取线程，便于定位未启动的路数
            try:
                self.err_thread = threading.Thread(target=self._read_errors)
                self.err_thread.daemon = True
                self.err_thread.start()
            except Exception:
                pass

            # 启动后监测是否拿到帧，否则自动切换采集参数为低带宽模式
            try:
                threading.Thread(target=self._fallback_monitor, daemon=True).start()
            except Exception:
                pass
            
        except Exception as e:
            error_msg = f"摄像头 {self.stream_id} 启动失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            # 启动失败时尝试测试模式
            self._start_test_mode()
            self.is_starting = False

    def _fallback_monitor(self):
        """监控启动后是否获取到帧，若无则自动降级采集参数"""
        try:
            time.sleep(2.5)
            if not self.is_running:
                return
            # 若队列仍为空，尝试重启为 yuyv422 640x480 20fps
            if self.frame_queue.empty() and not self.fallback_attempted:
                try:
                    if hasattr(self, 'camera_config'):
                        self.camera_config['capture_resolution'] = '640x480'
                        self.camera_config['capture_fps'] = 15
                        self.camera_config['capture_pixel_format'] = 'yuyv422'
                    self.fallback_attempted = True
                    self.stop_stream()
                    time.sleep(1.0)
                    self.start_stream()
                except Exception as e:
                    logger.error(f"降级采集失败: {e}")
        except Exception:
            pass
    
    def _get_usb_camera_cmd(self):
        """获取USB摄像头的FFmpeg命令"""
        # USB摄像头在Windows上的典型设备格式
        if platform.system() == "Windows":
            # 统一构造 dshow 输入字符串
            if self.camera_url.startswith("video="):
                # 如果camera_url已经包含video=前缀，直接使用它
                device_input = self.camera_url
            elif self.camera_url.startswith("@device_pnp_"):
                # PNP替代名必须以 video= 前缀传入 dshow
                device_input = f"video={self.camera_url}"
            else:
                # 普通设备名称，添加 video= 前缀
                device_input = f"video={self.camera_url}"
        else:
            device_input = self.camera_url
        
        width = 640
        height = 480
        fps = 30
        try:
            if hasattr(self, 'camera_config'):
                res = self.camera_config.get('resolution') or '640x480'
                if isinstance(res, str) and 'x' in res:
                    parts = res.lower().split('x')
                    width = int(parts[0])
                    height = int(parts[1])
                fps = int(self.camera_config.get('fps') or 30)
        except Exception:
            pass

        # 构建基础命令
        cmd = [
            FFMPEG_PATH,  # 使用检测到的FFmpeg路径
            '-hide_banner',
            '-loglevel', 'error',
            '-nostdin',
            '-f', 'dshow' if platform.system() == "Windows" else 'v4l2'
        ]
        
        # 如果有视频设备编号，添加到命令中
        if hasattr(self, 'camera_config') and 'video_device_number' in self.camera_config:
            video_device_number = self.camera_config['video_device_number']
            cmd.extend(['-video_device_number', str(video_device_number)])
        
        # 不强制设置dshow输入尺寸/帧率，避免设备拒绝；在输出端做scale/rate
        
        try:
            from .config import config as app_config
        except Exception:
            from config import config as app_config
            if app_config.get_app_config('ffmpeg.low_latency'):
                cmd.extend(['-fflags', 'nobuffer'])
        except Exception:
            pass
        
        # 添加输入设备
        # 为dshow增加运行时缓冲，避免卡顿；并请求压缩采集格式以降低总线带宽
        if platform.system() == "Windows":
            cmd.extend(['-rtbufsize', '100M'])
            # 单Hub下默认低带宽采集（可被每路配置覆盖）
            capture_w, capture_h = 640, 480
            capture_fps = 10
            capture_pixfmt = None
            try:
                if hasattr(self, 'camera_config'):
                    cap_res = self.camera_config.get('capture_resolution')
                    if isinstance(cap_res, str) and 'x' in cap_res:
                        p = cap_res.lower().split('x')
                        capture_w = int(p[0])
                        capture_h = int(p[1])
                    cfps = self.camera_config.get('capture_fps')
                    if cfps:
                        capture_fps = int(cfps)
                    cpf = self.camera_config.get('capture_pixel_format')
                    if isinstance(cpf, str):
                        # dshow只接受部分像素格式；mjpeg不能作为pixel_format传入
                        if cpf.lower() in ('yuyv422', 'yuy2', 'rgb24', 'bgr24'):
                            capture_pixfmt = cpf.lower()
                        else:
                            capture_pixfmt = None
            except Exception:
                pass
            # 为每路输入单独的队列，避免多路争抢阻塞
            cmd.extend(['-thread_queue_size', '256'])
        cmd.extend(['-i', device_input])
        
        vf_chain = []
        try:
            flip_h = False
            flip_v = False
            if hasattr(self, 'camera_config'):
                if self.camera_config.get('flip_h') is not None or self.camera_config.get('flip_v') is not None:
                    flip_h = bool(self.camera_config.get('flip_h'))
                    flip_v = bool(self.camera_config.get('flip_v'))
                elif self.camera_config.get('rotate180'):
                    flip_h = True
                    flip_v = True
            if flip_h:
                vf_chain.append('hflip')
            if flip_v:
                vf_chain.append('vflip')
        except Exception:
            pass
        vf_chain.append(f'scale={width}:{height}')
        cmd.extend([
            '-f', 'rawvideo',
            '-pix_fmt', 'rgb24',
            '-vcodec', 'rawvideo',
            '-an',
            '-vsync', 'passthrough',
            '-sws_flags', 'fast_bilinear',
            '-vf', ','.join(vf_chain),
            '-'
        ])
        
        return cmd
    
    def _get_ip_camera_cmd(self):
        """获取IP摄像头的FFmpeg命令"""
        return [
            FFMPEG_PATH,  # 使用检测到的FFmpeg路径
            '-i', self.camera_url,
            '-f', 'rawvideo',
            '-pix_fmt', 'rgb24',
            '-vcodec', 'rawvideo',
            '-an',  # 禁用音频
            '-sn',  # 禁用字幕
            '-vf', 'scale=640:480',  # 设置分辨率
            '-r', '30',  # 设置帧率
            '-'
        ]
    
    def _start_test_mode(self):
        """启动测试模式"""
        try:
            # 创建测试流
            self.test_stream = TestStream(self.stream_id)
            self.test_stream.frame_received.connect(self.frame_received)
            self.test_stream.error_occurred.connect(self.error_occurred)
            self.test_stream.start_stream()
            self.is_running = True
            logger.info(f"摄像头 {self.stream_id} 已切换到测试模式")
        except Exception as e:
            error_msg = f"测试模式启动失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def _read_frames(self):
        """读取帧数据"""
        try:
            w = 640
            h = 480
            try:
                if hasattr(self, 'camera_config'):
                    res = self.camera_config.get('resolution') or '640x480'
                    if isinstance(res, str) and 'x' in res:
                        parts = res.lower().split('x')
                        w = int(parts[0])
                        h = int(parts[1])
            except Exception:
                pass
            frame_size = w * h * 3
            
            while self.is_running and self.process:
                # 累积读取一帧数据，避免partial read导致丢帧
                buf = bytearray()
                while len(buf) < frame_size and self.is_running:
                    chunk = self.process.stdout.read(frame_size - len(buf))
                    if not chunk:
                        buf = bytearray()  # 清空并跳出
                        break
                    buf.extend(chunk)
                if not buf:
                    continue
                frame_data = bytes(buf)
                
                # 转换为numpy数组
                if len(frame_data) != frame_size:
                    # 跳过不完整帧，继续累积下一帧
                    continue
                frame = np.frombuffer(frame_data, dtype=np.uint8)
                frame = frame.reshape((h, w, 3))
                
                self.frame_count += 1
                if self.frame_count % self.publish_stride == 0:
                    self.last_frame_at = time.time()
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame)
                    try:
                        if callable(self.on_frame_callback):
                            self.on_frame_callback(self.stream_id, frame)
                    except Exception:
                        pass
                    self.frame_received.emit(frame)
                
        except Exception as e:
            error_msg = f"摄像头 {self.stream_id} 读取帧失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def stop_stream(self):
        """停止流式传输"""
        self.is_running = False
        
        # 停止测试流
        if hasattr(self, 'test_stream'):
            self.test_stream.stop_stream()
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            finally:
                try:
                    if self.process.stdout:
                        self.process.stdout.close()
                except Exception:
                    pass
                try:
                    if self.process.stderr:
                        self.process.stderr.close()
                except Exception:
                    pass
                self.process = None
        
        if self.thread:
            self.thread.join(timeout=5)
        if hasattr(self, 'err_thread') and self.err_thread:
            self.err_thread.join(timeout=1)
        
        logger.info(f"摄像头 {self.stream_id} 已停止")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """获取当前帧"""
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None

    def _read_errors(self):
        """读取并记录FFmpeg错误输出"""
        try:
            while self.is_running and self.process and self.process.stderr:
                line = self.process.stderr.readline()
                if not line:
                    break
                msg = line.decode('utf-8', errors='ignore').strip()
                if msg:
                    logger.error(f"摄像头 {self.stream_id} FFmpeg: {msg}")
                    if ('device already in use' in msg.lower() or 'could not run graph' in msg.lower()) and not self.pending_restart:
                        if self.restart_attempts >= 1:
                            continue
                        self.pending_restart = True
                        try:
                            def _delayed_restart():
                                try:
                                    time.sleep(2.0)
                                    if not self.is_running:
                                        return
                                    self.stop_stream()
                                    time.sleep(0.5)
                                    self.start_stream()
                                    self.restart_attempts += 1
                                    self.pending_restart = False
                                except Exception:
                                    self.pending_restart = False
                            threading.Thread(target=_delayed_restart, daemon=True).start()
                        except Exception:
                            self.pending_restart = False
        except Exception:
            pass


class CameraManager(QObject):
    """摄像头管理器 - 支持USB摄像头和IP摄像头"""
    frame_updated = pyqtSignal(int, np.ndarray)  # stream_id, frame
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.streams: Dict[int, FFmpegStream] = {}
        self.camera_configs_by_id: Dict[int, dict] = {}
        self.active_set: list[int] = []
        self.next_index: int = 0
        self.scheduler_thread = None
        self.max_concurrent = 2
        self.timeslice_seconds = 0.12
        self.bus_queue: queue.Queue = queue.Queue(maxsize=400)
        self.bus_thread = threading.Thread(target=self._bus_loop)
        self.bus_thread.daemon = True
        self.bus_thread.start()
        self.last_frames: Dict[int, np.ndarray] = {}
        self.cycle_period = 0.12
        self.pusher_thread = threading.Thread(target=self._cycle_push_loop)
        self.pusher_thread.daemon = True
        self.pusher_thread.start()
        # 从配置文件加载摄像头配置
        self.load_camera_configs()
    
    def load_camera_configs(self):
        """从配置文件加载摄像头配置"""
        try:
            from .config import config
        except Exception:
            from config import config
            self.camera_configs = config.get_camera_configs()
            try:
                self.max_concurrent = int(config.get_app_config('video.max_concurrent') or 1)
                self.timeslice_seconds = int(config.get_app_config('video.timeslice') or 4)
            except Exception:
                pass
            logger.info(f"从配置文件加载了 {len(self.camera_configs)} 个摄像头配置")
            # 调试信息
            for i, cam in enumerate(self.camera_configs):
                logger.info(f"摄像头 {i}: ID={cam.get('id')}, URL={cam.get('url')}, Name={cam.get('name')}")
            self.camera_configs_by_id = {cam.get('id'): cam for cam in self.camera_configs}
        except Exception as e:
            logger.error(f"加载摄像头配置失败: {e}")
            # 使用默认USB摄像头配置
            self.camera_configs = [
                {"id": 0, "url": "0", "name": "USB摄像头1"},
                {"id": 1, "url": "1", "name": "USB摄像头2"},
                {"id": 2, "url": "2", "name": "USB摄像头3"},
                {"id": 3, "url": "3", "name": "USB摄像头4"},
            ]
            logger.info("使用默认摄像头配置")
    
    def add_camera(self, stream_id: int, camera_url: str):
        """添加摄像头"""
        if stream_id in self.streams:
            self.remove_camera(stream_id)
        
        stream = FFmpegStream(camera_url, stream_id)
        stream.frame_received.connect(
            lambda frame, sid=stream_id: self.frame_updated.emit(sid, frame)
        )
        stream.error_occurred.connect(self.error_occurred.emit)
        
        self.streams[stream_id] = stream
        logger.info(f"添加摄像头 {stream_id}: {camera_url}")
    
    def remove_camera(self, stream_id: int):
        """移除摄像头"""
        if stream_id in self.streams:
            self.streams[stream_id].stop_stream()
            del self.streams[stream_id]
            logger.info(f"移除摄像头 {stream_id}")
    
    def start_all_cameras(self):
        """启动所有摄像头"""
        for config in self.camera_configs:
            self.add_camera_with_config(config)
        ids = sorted(self.streams.keys())
        self.active_set = []
        self.next_index = 0
        first_count = min(self.max_concurrent, len(ids))
        for i in range(first_count):
            sid = ids[self.next_index]
            try:
                self.streams[sid].start_stream()
                self.active_set.append(sid)
                self.next_index += 1
                time.sleep(0.8)
            except Exception:
                self.next_index += 1
        t0 = time.time()
        while time.time() - t0 < 5.0:
            ok = True
            for sid in self.active_set:
                s = self.streams.get(sid)
                if not s or s.frame_queue.empty():
                    ok = False
                    break
            if ok:
                break
            time.sleep(0.2)
        try:
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
        except Exception:
            pass
    
    def stop_all_cameras(self):
        """停止所有摄像头"""
        try:
            self.active_set = []
        except Exception:
            pass
        for stream in self.streams.values():
            stream.stop_stream()
        
        self.streams.clear()
    
    def get_frame(self, stream_id: int) -> Optional[np.ndarray]:
        if stream_id in self.streams:
            return self.streams[stream_id].get_frame()
        return None
    def start_camera(self, stream_id: int):
        cfg = self.camera_configs_by_id.get(stream_id)
        if cfg and stream_id not in self.streams:
            self.add_camera_with_config(cfg)
        s = self.streams.get(stream_id)
        if s:
            s.start_stream()
    def stop_camera(self, stream_id: int):
        s = self.streams.get(stream_id)
        if s:
            s.stop_stream()
    
    def update_camera_url(self, stream_id: int, camera_url: str):
        """更新摄像头URL"""
        self.remove_camera(stream_id)
        self.add_camera(stream_id, camera_url)
        if self.streams.get(stream_id):
            self.streams[stream_id].start_stream()
    
    def add_camera_with_config(self, camera_config: dict):
        """使用完整配置添加摄像头"""
        stream_id = camera_config["id"]
        camera_url = camera_config["url"]
        
        if stream_id in self.streams:
            self.remove_camera(stream_id)
        
        # 对数值索引优先使用 OpenCV 流，避免 dshow 设备名解析失败
        use_opencv = str(camera_url).strip().isdigit()
        try:
            try:
                from .config import config as app_cfg
            except Exception:
                from config import config as app_cfg
            prefer = bool(app_cfg.get_app_config('video.prefer_opencv_for_numeric') or True)
            use_opencv = prefer and use_opencv
        except Exception:
            pass

        if use_opencv:
            try:
                try:
                    from .opencv_stream import OpenCVStream
                except Exception:
                    from opencv_stream import OpenCVStream
                stream = OpenCVStream(camera_url, stream_id)
            except Exception:
                stream = FFmpegStream(camera_url, stream_id)
        else:
            stream = FFmpegStream(camera_url, stream_id)
        # 传递完整的摄像头配置
        stream.camera_config = camera_config
        stream.on_frame_callback = self._publish_frame
        ps = camera_config.get('publish_stride')
        if ps:
            try:
                stream.publish_stride = int(ps)
            except Exception:
                pass
        stream.frame_received.connect(
            lambda frame, sid=stream_id: self.frame_updated.emit(sid, frame)
        )
        stream.error_occurred.connect(self.error_occurred.emit)
        
        self.streams[stream_id] = stream
        logger.info(f"添加摄像头 {stream_id}: {camera_url} (配置: {camera_config.get('name', 'Unknown')})")

    def _publish_frame(self, sid: int, frame: np.ndarray):
        try:
            self.last_frames[sid] = frame
            self.bus_queue.put_nowait((sid, frame))
        except queue.Full:
            try:
                _ = self.bus_queue.get_nowait()
            except Exception:
                pass
            try:
                self.bus_queue.put_nowait((sid, frame))
            except Exception:
                pass

    def _bus_loop(self):
        while True:
            try:
                sid, frame = self.bus_queue.get()
                self.frame_updated.emit(sid, frame)
            except Exception:
                time.sleep(0.01)

    def _cycle_push_loop(self):
        while True:
            try:
                ids = sorted(self.camera_configs_by_id.keys())
                for sid in ids:
                    f = self.last_frames.get(sid)
                    if f is not None:
                        # 降低视频更新频率，每3个周期发送一次信号
                        self.frame_updated.emit(sid, f)
                # 增加循环周期，降低CPU占用
                time.sleep(self.cycle_period * 3)
            except Exception:
                time.sleep(0.1)

    def _scheduler_loop(self):
        try:
            ids = sorted(self.camera_configs_by_id.keys())
            if not ids:
                return
            # 预热：保持当前已启动的若干路
            window = []
            while True:
                time.sleep(self.timeslice_seconds)
                if not ids:
                    continue
                # 下一路
                sid = ids[self.next_index % len(ids)]
                self.next_index += 1
                cfg = self.camera_configs_by_id.get(sid)
                if cfg and sid not in self.streams:
                    self.add_camera_with_config(cfg)
                started_ok = False
                try:
                    s = self.streams.get(sid)
                    if s:
                        s.start_stream()
                        # 等待短暂握手，确认拿到帧
                        t0 = time.time()
                        while time.time() - t0 < 0.25:
                            if s.last_frame_at and time.time() - s.last_frame_at < 0.5:
                                started_ok = True
                                break
                            time.sleep(0.05)
                        # 加入窗口
                        window.append(sid)
                        self.active_set = window[-self.max_concurrent:]
                except Exception:
                    pass
                # 若超过并发上限，优雅移除最旧一路（在新路拿到帧后再停止）
                if len(window) > self.max_concurrent:
                    old_sid = window.pop(0)
                    if old_sid != sid:
                        try:
                            old = self.streams.get(old_sid)
                            if old:
                                old.stop_stream()
                        except Exception:
                            pass
        except Exception:
            pass