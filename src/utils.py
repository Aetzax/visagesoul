"""
Helper utilities for VisageSoul: logging, camera detection, audio feedback, and image enhancement.
"""

import os
import sys
import glob
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import cv2
import numpy as np


def setup_logger(name: str = "visagesoul", debug: bool = False, log_file: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.DEBUG if debug else logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception:
            pass

    return logger


def play_chime(sound_type: str = "success", volume_pct: Optional[int] = None):
    """
    Plays a subtle, pleasant system sound chime asynchronously at controlled volume.
    Uses pw-play, paplay, or canberra-gtk-play in the background.
    """
    sound_map = {
        "success": "service-login",
        "match": "complete",
        "fail": "dialog-warning",
    }
    event_id = sound_map.get(sound_type, "service-login")

    if volume_pct is None:
        try:
            from .config import config
            volume_pct = config.getint("security", "sound_volume", 35)
        except Exception:
            volume_pct = 35

    # Clamp volume between 0 and 100
    volume_pct = max(0, min(100, volume_pct))
    if volume_pct == 0:
        return

    vol_float = volume_pct / 100.0
    pa_vol = int((volume_pct / 100.0) * 65536)

    # Search for audio file
    sound_files = [
        f"/usr/share/sounds/freedesktop/stereo/{event_id}.oga",
        f"/usr/share/sounds/freedesktop/stereo/{event_id}.ogg",
        f"/usr/share/sounds/freedesktop/stereo/{event_id}.wav",
    ]
    target_sound = next((f for f in sound_files if os.path.exists(f)), None)

    try:
        if target_sound and shutil_which("pw-play"):
            subprocess.Popen(
                ["pw-play", f"--volume={vol_float:.2f}", target_sound],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        elif target_sound and shutil_which("paplay"):
            subprocess.Popen(
                ["paplay", f"--volume={pa_vol}", target_sound],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        elif shutil_which("canberra-gtk-play"):
            subprocess.Popen(
                ["canberra-gtk-play", "-i", event_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    except Exception:
        pass


def shutil_which(cmd: str) -> Optional[str]:
    import shutil
    return shutil.which(cmd)


def check_and_boost_light(frame: np.ndarray, threshold: float = 65.0) -> Tuple[np.ndarray, bool]:
    """
    Analyzes average frame luminance. If in dark room/low light, applies CLAHE
    (Contrast Limited Adaptive Histogram Equalization) on the L-channel to reveal faces.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    avg_brightness = np.mean(gray)

    if avg_brightness < threshold:
        # Low light condition -> apply adaptive contrast enhancement
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        return enhanced, True

    return frame, False


def list_video_devices() -> List[Dict[str, str]]:
    """Lists available V4L2 video capture devices with names and paths."""
    devices = []
    video_paths = sorted(glob.glob("/dev/video*"))

    for dev in video_paths:
        try:
            dev_num_str = dev.replace("/dev/video", "")
            if not dev_num_str.isdigit():
                continue
            dev_idx = int(dev_num_str)

            name_file = f"/sys/class/video4linux/video{dev_idx}/name"
            name = "Unknown Camera"
            if os.path.isfile(name_file):
                with open(name_file, "r") as f:
                    name = f.read().strip()

            index_file = f"/sys/class/video4linux/video{dev_idx}/index"
            if os.path.isfile(index_file):
                with open(index_file, "r") as f:
                    if f.read().strip() != "0":
                        continue

            devices.append({
                "path": dev,
                "name": name,
                "id": str(dev_idx),
            })
        except Exception:
            pass

    return devices


def open_camera(device_path: str = "/dev/video0", width: int = 1280, height: int = 720, fourcc_str: str = "MJPG", fps: int = 30) -> Optional[cv2.VideoCapture]:
    """Opens and configures the camera with optimal parameters for Logitech StreamCam."""
    cap = None
    dev_num_str = device_path.replace("/dev/video", "")

    if dev_num_str.isdigit():
        dev_idx = int(dev_num_str)
        cap = cv2.VideoCapture(dev_idx, cv2.CAP_V4L2)
        if not cap or not cap.isOpened():
            cap = cv2.VideoCapture(dev_idx)

    if cap is None or not cap.isOpened():
        cap = cv2.VideoCapture(device_path)

    if not cap or not cap.isOpened():
        return None

    if fourcc_str:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc_str))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    return cap


def warmup_camera(cap: cv2.VideoCapture, frames: int = 5):
    """Discards initial frames to let the sensor adjust auto-exposure and white balance."""
    for _ in range(max(1, frames)):
        cap.grab()


class CursorFeedbackManager:
    """
    Triggers desktop cursor feedback (bouncing app icon in KDE / GNOME)
    and transient OSD notification while PAM biometric verification is active.
    """
    def __init__(self, enabled: bool = True, osd_enabled: bool = True, message: str = "Esperando biometría..."):
        self.enabled = enabled
        self.osd_enabled = osd_enabled
        self.message = message
        self.proc = None

    def __enter__(self):
        if not self.enabled and not self.osd_enabled:
            return self

        # 1. Trigger cursor busy / launching animation in KDE / Wayland / X11
        if self.enabled:
            kstart = shutil_which("kstart") or shutil_which("kstart5")
            if kstart:
                try:
                    self.proc = subprocess.Popen(
                        [kstart, "--desktopfile", "visagesoul.desktop", "sleep", "4"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass

        # 2. Trigger sleek transient OSD notification banner
        if self.osd_enabled and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            notify_send = shutil_which("notify-send")
            if notify_send:
                try:
                    subprocess.Popen(
                        [
                            notify_send,
                            "-a", "VisageSoul",
                            "-i", "visagesoul",
                            "-h", "string:x-canonical-private-synchronous:visagesoul_auth",
                            "-u", "low",
                            "-t", "2500",
                            "VisageSoul",
                            self.message
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.kill()
            except Exception:
                pass
