#!/usr/bin/env python3
"""
Fast verification script executed by PAM for VisageSoul.
Returns:
  0: Authentication SUCCESS (face matched + gesture if required)
  1: Authentication FAILURE (timeout or mismatch)
  2: System/Camera Error (fallback to password immediately)
  3: Max Failed Attempts Exceeded (lockout -> force password)
"""

import sys
import os

# Suppress internal C++ logging from OpenCV, TensorFlow Lite and MediaPipe
os.environ["GLOG_minloglevel"] = "3"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

import json
import time
import argparse
import subprocess
from pathlib import Path

# Add src parent directory to sys.path if needed
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir.parent))

from src.config import config
from src.utils import setup_logger, open_camera, warmup_camera, play_chime, check_and_boost_light
from src.engine import FaceEngine, GestureEngine


def get_attempts_file(username: str) -> Path:
    # Use secure /run/visagesoul or isolated directory to prevent symlink attacks
    run_dir = Path("/run/visagesoul")
    if run_dir.is_dir():
        return run_dir / f"attempts_{username}.json"

    secure_dir = Path("/tmp/visagesoul_runtime")
    try:
        secure_dir.mkdir(mode=0o1777, parents=True, exist_ok=True)
    except Exception:
        pass
    return secure_dir / f"attempts_{username}.json"


def check_attempt_limit(username: str, max_attempts: int = 3, window_seconds: int = 300) -> bool:
    """Returns True if user is allowed to attempt facial auth, False if locked out."""
    if max_attempts <= 0:
        return True

    state_file = get_attempts_file(username)
    if not state_file.is_file():
        return True

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        now = time.time()
        valid_timestamps = [t for t in data.get("timestamps", []) if (now - t) < window_seconds]
        return len(valid_timestamps) < max_attempts
    except Exception:
        return True


def record_failed_attempt(username: str, window_seconds: int = 300):
    state_file = get_attempts_file(username)
    try:
        now = time.time()
        timestamps = []
        if state_file.is_file():
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            timestamps = [t for t in data.get("timestamps", []) if (now - t) < window_seconds]
        timestamps.append(now)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"timestamps": timestamps}, f)
        try:
            os.chmod(state_file, 0o666)
        except Exception:
            pass
    except Exception:
        pass


def reset_attempts(username: str):
    state_file = get_attempts_file(username)
    if state_file.is_file():
        try:
            state_file.unlink()
        except Exception:
            pass


def verify_user(username: str, timeout: float = None, threshold: float = None, device_path: str = None, debug: bool = False, require_thumbs_up: bool = None, gesture_type: str = None) -> int:
    is_debug = True
    log_file = "/tmp/visagesoul_verify.log"
    logger = setup_logger("visagesoul-verify", debug=is_debug, log_file=log_file)

    if timeout is None:
        timeout = config.getfloat("security", "timeout", 4.5)
    if threshold is None:
        threshold = config.getfloat("security", "threshold", 0.70)
    if device_path is None:
        device_path = config.get("camera", "device", "/dev/video0")
    if require_thumbs_up is None:
        require_gesture = config.getboolean("security", "require_gesture", config.getboolean("security", "require_thumbs_up", False))
    else:
        require_gesture = require_thumbs_up

    if gesture_type is None:
        gesture_type = config.get("security", "gesture_type", "thumb_up").lower()

    max_attempts = config.getint("security", "max_attempts", 3)
    attempts_window = config.getint("security", "attempts_window", 300)
    auto_unlock = config.getboolean("security", "auto_unlock", True)
    low_light_boost = config.getboolean("camera", "low_light_boost", True)
    sound_feedback = config.getboolean("security", "sound_feedback", True)

    logger.info(f"=== Starting VisageSoul verification for user '{username}' ===")
    logger.info(f"Parameters: timeout={timeout}s, threshold={threshold}, gesture={require_gesture} ({gesture_type}), max_attempts={max_attempts}")

    # Check attempt limit
    if not check_attempt_limit(username, max_attempts=max_attempts, window_seconds=attempts_window):
        logger.warning(f"User '{username}' exceeded max failed attempts ({max_attempts}). Forcing password.")
        return 3

    # 1. Initialize FaceEngine and check if profile exists
    try:
        engine = FaceEngine()
        gesture_engine = GestureEngine() if require_gesture else None
        from src.engine import BlinkEngine
        blink_engine = BlinkEngine()
    except Exception as e:
        logger.error(f"Failed to initialize FaceEngine: {e}")
        return 2

    user_embeddings = engine.load_profile(username)
    if not user_embeddings:
        logger.warning(f"No enrolled face profile found for user '{username}'.")
        return 1

    # 2. Check if video device exists
    if not os.path.exists(device_path):
        logger.warning(f"Camera device {device_path} not found.")
        return 2

    # 3. Open Camera
    width = config.getint("camera", "width", 1280)
    height = config.getint("camera", "height", 720)
    fourcc = config.get("camera", "fourcc", "MJPG")
    fps = config.getint("camera", "fps", 30)
    warmup_frames = config.getint("camera", "warmup_frames", 6)

    cap = open_camera(device_path, width, height, fourcc, fps)
    if cap is None:
        logger.error(f"Unable to access camera {device_path}.")
        return 2

    liveness_check = config.getboolean("security", "liveness_check", True)

    try:
        # Sensor warmup
        warmup_camera(cap, warmup_frames)

        start_time = time.time()
        consecutive_matches = 0
        REQUIRED_CONSECUTIVE_MATCHES = config.getint("security", "consecutive_matches", 5)
        frame_idx = 0

        while (time.time() - start_time) < timeout:
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            frame_idx += 1
            faces = engine.detect_faces(frame)
            primary = engine.get_primary_face(faces)

            if primary is not None:
                target_emb = engine.extract_embedding(frame, primary)
                is_match, score = engine.verify_against_profile(target_emb, user_embeddings, threshold=threshold)

                # Anti-spoofing FAS multi-layer check (Screens, Photos, Replays)
                liveness_passed = True
                liveness_msg = "OK"
                liveness_score = 1.0
                if liveness_check:
                    liveness_passed, liveness_score, liveness_msg = engine.check_liveness(frame, primary)

                metrics = engine.get_last_antispoof_metrics()
                p_real = metrics.get("p_real", 0.0)
                p_screen = metrics.get("p_screen", 0.0)
                rigidity = metrics.get("rigidity_score", 0.0)
                eye_std = metrics.get("eye_std", 0.0)

                gesture_ok = True
                g_name = "N/A"
                g_metrics = {}
                if require_gesture and gesture_engine:
                    gesture_ok, g_name = gesture_engine.is_gesture_valid(frame, mode=gesture_type, primary_face=primary)
                    g_metrics = gesture_engine.get_last_metrics()

                raw_g = g_metrics.get("raw_gesture", "None")
                raw_s = g_metrics.get("raw_score", 0.0)
                g_dist = g_metrics.get("rel_dist", 0.0)
                g_std = g_metrics.get("std_dist", 0.0)
                g_reason = g_metrics.get("reason", "N/A")

                logger.debug(
                    f"Frame #{frame_idx:02d}: Match={is_match} ({score:.3f}/{threshold:.2f}) | "
                    f"Live={liveness_passed} (Real:{p_real*100:.0f}%, Screen:{p_screen*100:.0f}%, Rigidity:{rigidity:.5f}, EyeStd:{eye_std:.4f} -> {liveness_msg}) | "
                    f"Gesture={gesture_ok} (Raw:{raw_g}:{raw_s:.2f}, Dist:{g_dist:.2f}x, StdDist:{g_std:.4f} -> {g_reason}) | "
                    f"Cons={consecutive_matches}/{REQUIRED_CONSECUTIVE_MATCHES}"
                )

                # Check blink
                has_blinked = blink_engine.detect_blink(frame)
                if not has_blinked:
                    logger.info("Esperando parpadeo para confirmar vida...")
                    liveness_passed = False

                if is_match and liveness_passed:
                    if require_gesture and gesture_engine:
                        if gesture_ok:
                            consecutive_matches += 1
                            if consecutive_matches >= REQUIRED_CONSECUTIVE_MATCHES:
                                logger.info(f"Verification SUCCESS for {username} (Face + 3D Live + {g_name})! (Score: {score:.3f})")
                                reset_attempts(username)
                                if sound_feedback:
                                    play_chime("success")
                                if auto_unlock:
                                    try:
                                        subprocess.Popen(["loginctl", "unlock-session"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                    except Exception:
                                        pass
                                return 0
                        else:
                            consecutive_matches = 0
                    else:
                        consecutive_matches += 1
                        if consecutive_matches >= REQUIRED_CONSECUTIVE_MATCHES:
                            logger.info(f"Verification SUCCESS for {username}! (Score: {score:.3f})")
                            reset_attempts(username)
                            if sound_feedback:
                                play_chime("success")
                            if auto_unlock:
                                try:
                                    subprocess.Popen(["loginctl", "unlock-session"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                except Exception:
                                    pass
                            return 0
                else:
                    consecutive_matches = 0
            else:
                consecutive_matches = 0
                logger.debug(f"Frame #{frame_idx:02d}: No face detected")

            time.sleep(0.02)

        logger.info(f"Verification timed out ({timeout}s) for user {username}.")
        record_failed_attempt(username, window_seconds=attempts_window)
        return 1

    except Exception as e:
        logger.error(f"Exception during verification: {e}")
        return 2
    finally:
        if cap is not None:
            cap.release()


def main():
    parser = argparse.ArgumentParser(description="VisageSoul Verification Helper")
    parser.add_argument("--user", "-u", default=os.environ.get("PAM_USER") or os.environ.get("USER"), help="Target username")
    parser.add_argument("--timeout", "-t", type=float, default=None, help="Timeout in seconds")
    parser.add_argument("--threshold", "-s", type=float, default=None, help="Match threshold (0.0-1.0)")
    parser.add_argument("--device", "-d", default=None, help="Camera device path")
    parser.add_argument("--require-thumbs-up", action="store_true", default=None, help="Require thumbs up gesture")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if not args.user:
        print("Error: No user specified.", file=sys.stderr)
        sys.exit(2)

    exit_code = verify_user(
        username=args.user,
        timeout=args.timeout,
        threshold=args.threshold,
        device_path=args.device,
        debug=args.debug or config.getboolean("pam", "debug", False),
        require_thumbs_up=args.require_thumbs_up,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
