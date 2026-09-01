"""
Configuration manager for VisageSoul.
Loads and saves configuration parameters with robust fallbacks and user-level overrides.
"""

import os
import configparser
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_PATHS = [
    Path.home() / ".config" / "visagesoul" / "config.ini",
    Path("/etc/visagesoul/config.ini"),
    Path("/etc/aura-auth/config.ini"),
    Path(__file__).resolve().parent.parent / "config" / "config.ini",
]

DEFAULT_CONFIG = {
    "general": {
        "language": "auto",
    },
    "camera": {
        "device": "/dev/video0",
        "width": "1280",
        "height": "720",
        "fourcc": "MJPG",
        "fps": "30",
        "warmup_frames": "5",
        "low_light_boost": "true",
    },
    "security": {
        "threshold": "0.70",
        "timeout": "4.5",
        "min_face_size": "60",
        "liveness_check": "true",
        "require_thumbs_up": "true",
        "require_gesture": "true",
        "gesture_type": "thumb_up",
        "auto_unlock": "true",
        "sound_feedback": "true",
        "sound_volume": "35",
        "max_attempts": "3",
        "attempts_window": "300",
    },
    "paths": {
        "models_dir": "/usr/share/visagesoul/models",
        "faces_dir": "/etc/visagesoul/faces",
        "log_file": "/var/log/visagesoul.log",
    },
    "pam": {
        "debug": "false",
        "notify": "true",
        "message": "Esperando biometría...",
    },
}


class Config:
    def __init__(self, custom_path: str = None):
        self.config = configparser.ConfigParser()
        # Populate defaults
        for section, values in DEFAULT_CONFIG.items():
            self.config[section] = values

        self.loaded_path = None
        if custom_path and Path(custom_path).is_file():
            self.config.read(custom_path)
            self.loaded_path = Path(custom_path)
        else:
            # Read system config first, then overlay user config if present
            system_cfg = Path("/etc/visagesoul/config.ini")
            if system_cfg.is_file():
                self.config.read(system_cfg)
                self.loaded_path = system_cfg

            user_cfg = Path.home() / ".config" / "visagesoul" / "config.ini"
            if user_cfg.is_file():
                self.config.read(user_cfg)
                self.loaded_path = user_cfg

            # Also check target user's home if running as root under PAM
            target_user = os.environ.get("PAM_USER") or os.environ.get("SUDO_USER")
            if target_user and target_user != "root":
                try:
                    import pwd
                    u_home = Path(pwd.getpwnam(target_user).pw_dir)
                    u_cfg = u_home / ".config" / "visagesoul" / "config.ini"
                    if u_cfg.is_file():
                        self.config.read(u_cfg)
                        self.loaded_path = u_cfg
                except Exception:
                    pass

        # Fallback local models_dir if running from source tree
        source_models_dir = Path(__file__).resolve().parent.parent / "models"
        if not Path(self.get("paths", "models_dir")).is_dir() and source_models_dir.is_dir():
            self.set("paths", "models_dir", str(source_models_dir))

        # Fallback local faces_dir if running as non-root from source
        source_faces_dir = Path.home() / ".local" / "share" / "visagesoul" / "faces"
        if not Path(self.get("paths", "faces_dir")).is_dir():
            if os.geteuid() != 0:
                source_faces_dir.mkdir(parents=True, exist_ok=True)
                self.set("paths", "faces_dir", str(source_faces_dir))

    def get(self, section: str, key: str, fallback: Any = None) -> str:
        return self.config.get(section, key, fallback=fallback)

    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        return self.config.getint(section, key, fallback=fallback)

    def getfloat(self, section: str, key: str, fallback: float = 0.0) -> float:
        return self.config.getfloat(section, key, fallback=fallback)

    def getboolean(self, section: str, key: str, fallback: bool = False) -> bool:
        return self.config.getboolean(section, key, fallback=fallback)

    def set(self, section: str, key: str, value: Any):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))

    def save(self, target_path: str = None) -> bool:
        if target_path:
            paths_to_try = [Path(target_path)]
        elif os.geteuid() == 0:
            paths_to_try = [
                Path("/etc/visagesoul/config.ini"),
                Path.home() / ".config" / "visagesoul" / "config.ini",
            ]
        else:
            paths_to_try = [
                Path.home() / ".config" / "visagesoul" / "config.ini",
                Path("/etc/visagesoul/config.ini"),
            ]

        for path in paths_to_try:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    self.config.write(f)
                self.loaded_path = path
                return True
            except PermissionError:
                continue
            except Exception as e:
                print(f"Error saving config to {path}: {e}")
        return False


# Global singleton instance
config = Config()
