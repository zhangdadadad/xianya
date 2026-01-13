# d:\LLM\Xiangya\cv-catch\ffmpeg_cat\services\guidance_service.py
import threading
import time
try:
    from .movement_guidance import MovementGuidance
except Exception:
    from movement_guidance import MovementGuidance

class GuidanceService:
    def __init__(self, state_getter, center_margin=0.2, target_area=0.12, min_interval=1.0):
        self.state_getter = state_getter
        self.center_margin = center_margin
        self.target_area = target_area
        self.min_interval = min_interval
        self._running = False
        self._thread = None
        self._last_at = 0.0
        self._hold_once = False
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
        except Exception:
            self._engine = None
        self._advisor = MovementGuidance(deadband=center_margin, area_target=target_area, area_tolerance=target_area * 0.3, alpha=0.6, hysteresis=0.05)

    def start(self):
        if self._running:
            return
        self._running = True
        self._hold_once = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        t = self._thread
        if t:
            try:
                t.join(timeout=0.5)
            except Exception:
                pass
        self._thread = None

    def hold(self):
        self._hold_once = True
        self._speak("好的，很好，保持住")

    def _speak(self, text: str):
        now = time.time()
        if now - self._last_at < self.min_interval:
            return
        self._last_at = now
        if self._engine:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                pass

    def _loop(self):
        while self._running:
            try:
                frame, boxes = self.state_getter()
                if frame is not None and boxes:
                    msgs = self._advisor.update(frame, boxes)
                    if msgs:
                        self._speak("，".join(msgs))
                        self._hold_once = False
                    else:
                        if not self._hold_once:
                            self._speak("好的，很好，保持住")
                            self._hold_once = True
                time.sleep(0.2)
            except Exception:
                time.sleep(0.2)