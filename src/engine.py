"""
Facial & Gestural Biometrics Engine for VisageSoul.
Uses OpenCV YuNet (Detection), SFace (Embedding Recognition), and MediaPipe (Gesture Tracking).
"""

import os
import json
import time
import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import cv2
import numpy as np

from .config import config
from .utils import setup_logger, check_and_boost_light

logger = setup_logger("visagesoul-engine")


class FaceEngine:
    def __init__(self, models_dir: Optional[str] = None):
        if models_dir is None:
            models_dir = config.get("paths", "models_dir")

        self.models_dir = Path(models_dir)
        self.detector_model_path = self.models_dir / "face_detection_yunet_2023mar.onnx"
        self.recognizer_model_path = self.models_dir / "face_recognition_sface_2021dec.onnx"

        if not self.detector_model_path.is_file():
            raise FileNotFoundError(f"YuNet model not found at {self.detector_model_path}")
        if not self.recognizer_model_path.is_file():
            raise FileNotFoundError(f"SFace model not found at {self.recognizer_model_path}")

        # Initialize YuNet Detector
        self.detector = cv2.FaceDetectorYN.create(
            str(self.detector_model_path),
            "",
            (320, 320),
            0.6,
            0.3,
            5000,
        )

        # Initialize SFace Recognizer
        self.recognizer = cv2.FaceRecognizerSF.create(
            str(self.recognizer_model_path),
            "",
        )

        self.faces_dir = Path(config.get("paths", "faces_dir"))
        self.faces_dir.mkdir(parents=True, exist_ok=True)

    def detect_faces(self, frame: np.ndarray, score_threshold: float = 0.6) -> List[np.ndarray]:
        """
        Detects faces in a frame using YuNet.
        Returns list of face arrays: [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm, score]
        """
        h, w, _ = frame.shape
        self.detector.setInputSize((w, h))
        self.detector.setScoreThreshold(score_threshold)
        _, faces = self.detector.detect(frame)
        if faces is None:
            return []
        return [f for f in faces]

    def get_primary_face(self, faces: List[np.ndarray], min_size: int = 60) -> Optional[np.ndarray]:
        """Finds the largest and highest confidence face in the frame."""
        if not faces:
            return None
        valid_faces = [f for f in faces if f[2] >= min_size and f[3] >= min_size]
        if not valid_faces:
            return None
        return max(valid_faces, key=lambda f: f[2] * f[3])

    def extract_embedding(self, frame: np.ndarray, face: np.ndarray) -> np.ndarray:
        """
        Aligns the face based on 5 landmarks and extracts a 128-dimensional embedding.
        """
        aligned_face = self.recognizer.alignCrop(frame, face)
        feature = self.recognizer.feature(aligned_face)
        feat_flat = feature.flatten().astype(np.float32)
        norm = np.linalg.norm(feat_flat)
        if norm > 0:
            feat_flat = feat_flat / norm
        return feat_flat

    def compare_embeddings(self, feat1: np.ndarray, feat2: np.ndarray) -> float:
        """
        Calculates cosine similarity between two 128-d face embeddings (range: -1.0 to 1.0).
        """
        feat1 = feat1.flatten()
        feat2 = feat2.flatten()
        dot_product = np.dot(feat1, feat2)
        norm1 = np.linalg.norm(feat1)
        norm2 = np.linalg.norm(feat2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))

    def verify_against_profile(self, target_embedding: np.ndarray, user_embeddings: List[np.ndarray], threshold: float = 0.70) -> Tuple[bool, float]:
        """
        Compares an extracted embedding against an enrolled user's model templates.
        Returns (is_match, max_similarity_score).
        """
        if not user_embeddings:
            return False, 0.0

        scores = [self.compare_embeddings(target_embedding, emb) for emb in user_embeddings]
        max_score = max(scores) if scores else 0.0
        return (max_score >= threshold), max_score

    def compute_liveness_score(self, face_history: List[np.ndarray]) -> float:
        """
        Analyzes 3D non-rigid parallax & landmark micro-fluctuations across consecutive frames.
        Computes standard deviation of yaw-asymmetry ratio and eye-to-mouth triangle proportions.
        Live humans exhibit natural 3D projective perspective changes and micro-saccades (> 0.0012),
        while flat 2D printed photos or phone screens move strictly as rigid 2D affine planes (~0.0000).
        """
        if len(face_history) < 3:
            return 0.01  # Initial bootstrap

        yaw_ratios = []
        tri_ratios = []
        for f in face_history:
            if len(f) < 14:
                continue
            re_x, re_y = float(f[4]), float(f[5])
            le_x, le_y = float(f[6]), float(f[7])
            nose_x, nose_y = float(f[8]), float(f[9])
            rcm_x, rcm_y = float(f[10]), float(f[11])
            lcm_x, lcm_y = float(f[12]), float(f[13])

            d_re_nose = np.sqrt((nose_x - re_x)**2 + (nose_y - re_y)**2)
            d_le_nose = np.sqrt((nose_x - le_x)**2 + (nose_y - le_y)**2)
            yaw_ratio = (d_re_nose - d_le_nose) / (d_re_nose + d_le_nose + 1e-6)

            eye_dist = np.sqrt((le_x - re_x)**2 + (le_y - re_y)**2)
            mouth_dist = np.sqrt((lcm_x - rcm_x)**2 + (lcm_y - rcm_y)**2)
            tri_ratio = eye_dist / (mouth_dist + 1e-6)

            yaw_ratios.append(yaw_ratio)
            tri_ratios.append(tri_ratio)

        if not yaw_ratios or not tri_ratios:
            return 0.0

        score = float(np.std(yaw_ratios) + np.std(tri_ratios))
        return score

    def get_profile_path(self, username: str) -> Path:
        return self.faces_dir / f"{username}.json"

    def save_profile(self, username: str, embeddings: List[np.ndarray], label: str = "Principal", append: bool = True, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Saves a user's face embeddings. If append=True, adds or updates the named aspect
        (e.g., 'Sin gafas', 'Con gafas') and aggregates all embeddings for recognition.
        """
        profile_path = self.get_profile_path(username)
        models = []
        created_at = datetime.datetime.now().isoformat()

        if append and profile_path.is_file():
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                created_at = existing_data.get("created_at", created_at)
                existing_models = existing_data.get("models", [])
                if existing_models:
                    # Filter out model with the same name to update it
                    models = [m for m in existing_models if m.get("name") != label]
                elif "embeddings" in existing_data and existing_data["embeddings"]:
                    # Migrate legacy single-model format
                    models = [{
                        "name": "Principal",
                        "created_at": created_at,
                        "sample_count": len(existing_data["embeddings"]),
                        "embeddings": existing_data["embeddings"]
                    }]
            except Exception as e:
                logger.warning(f"Could not read existing profile for {username}: {e}")

        # Append new sub-model
        models.append({
            "name": label,
            "created_at": datetime.datetime.now().isoformat(),
            "sample_count": len(embeddings),
            "embeddings": [emb.tolist() for emb in embeddings]
        })

        # Flatten all embeddings for rapid verification
        all_embeddings = []
        for m in models:
            all_embeddings.extend(m["embeddings"])

        data = {
            "username": username,
            "created_at": created_at,
            "updated_at": datetime.datetime.now().isoformat(),
            "sample_count": len(all_embeddings),
            "models": models,
            "embeddings": all_embeddings,
            "metadata": metadata or {},
        }

        try:
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = profile_path.with_suffix(f".tmp.{os.getpid()}")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            try:
                os.chmod(temp_path, 0o644)
            except Exception:
                pass
            os.replace(temp_path, profile_path)
            return True
        except Exception as e:
            logger.error(f"Failed to save profile for {username}: {e}")
            if "temp_path" in locals() and temp_path.is_file():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            return False

    def get_user_models(self, username: str) -> List[Dict[str, Any]]:
        """Returns list of sub-models for a user."""
        profile_path = self.get_profile_path(username)
        if not profile_path.is_file():
            return []
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "models" in data and data["models"]:
                return data["models"]
            elif "embeddings" in data:
                return [{
                    "name": "Principal",
                    "created_at": data.get("created_at", "Desconocido"),
                    "sample_count": len(data["embeddings"])
                }]
        except Exception:
            pass
        return []

    def delete_submodel(self, username: str, label: str) -> bool:
        """Deletes a specific submodel (e.g. 'Con gafas') for a user."""
        profile_path = self.get_profile_path(username)
        if not profile_path.is_file():
            return False
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            models = [m for m in data.get("models", []) if m.get("name") != label]
            if not models:
                return self.delete_profile(username)
            all_embeddings = []
            for m in models:
                all_embeddings.extend(m["embeddings"])
            data["models"] = models
            data["sample_count"] = len(all_embeddings)
            data["embeddings"] = all_embeddings
            data["updated_at"] = datetime.datetime.now().isoformat()
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error deleting submodel '{label}' for {username}: {e}")
            return False

    def load_profile(self, username: str) -> Optional[List[np.ndarray]]:
        """Loads enrolled embeddings for a username."""
        profile_path = self.get_profile_path(username)

        # Also check fallback aura-auth path if migrating
        if not profile_path.is_file():
            fallback_path = Path("/etc/aura-auth/faces") / f"{username}.json"
            if fallback_path.is_file():
                profile_path = fallback_path

        if not profile_path.is_file():
            return None

        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            embeddings = [np.array(emb, dtype=np.float32) for emb in data.get("embeddings", [])]
            return embeddings
        except Exception as e:
            logger.error(f"Failed to load profile for {username}: {e}")
            return None

    def list_enrolled_users(self) -> List[Dict[str, Any]]:
        """Returns list of enrolled users with their models."""
        users = []
        search_dirs = [self.faces_dir, Path("/etc/aura-auth/faces")]

        seen_users = set()
        for directory in search_dirs:
            if not directory.is_dir():
                continue
            for file in directory.glob("*.json"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    uname = data.get("username", file.stem)
                    if uname not in seen_users:
                        seen_users.add(uname)
                        models_list = data.get("models", [])
                        if not models_list and "embeddings" in data:
                            models_list = [{
                                "name": "Principal",
                                "sample_count": len(data["embeddings"]),
                                "created_at": data.get("created_at", "Unknown")
                            }]
                        users.append({
                            "username": uname,
                            "created_at": data.get("created_at", "Unknown"),
                            "sample_count": data.get("sample_count", len(data.get("embeddings", []))),
                            "models": models_list,
                            "file": str(file),
                        })
                except Exception:
                    pass
        return users

    def delete_profile(self, username: str) -> bool:
        """Deletes a user's face profile."""
        paths = [
            self.get_profile_path(username),
            Path("/etc/aura-auth/faces") / f"{username}.json"
        ]
        deleted = False
        for p in paths:
            if p.is_file():
                try:
                    p.unlink()
                    deleted = True
                except Exception as e:
                    logger.error(f"Failed to delete profile at {p}: {e}")
        return deleted


class GestureEngine:
    """
    Hand Gesture Recognition Engine using MediaPipe Tasks (Thumb_Up 👍, Open_Palm, Victory, etc.).
    """
    def __init__(self, models_dir: Optional[str] = None):
        if models_dir is None:
            models_dir = config.get("paths", "models_dir")
        self.models_dir = Path(models_dir)
        self.model_path = self.models_dir / "gesture_recognizer.task"
        self.recognizer = None

        if self.model_path.is_file():
            try:
                import mediapipe as mp
                from mediapipe.tasks import python
                from mediapipe.tasks.python import vision

                base_options = python.BaseOptions(model_asset_path=str(self.model_path))
                options = vision.GestureRecognizerOptions(
                    base_options=base_options,
                    running_mode=vision.RunningMode.IMAGE,
                    min_hand_detection_confidence=0.30,
                    min_tracking_confidence=0.30,
                )
                self.recognizer = vision.GestureRecognizer.create_from_options(options)
            except Exception as e:
                logger.warning(f"Could not initialize MediaPipe GestureRecognizer: {e}")

    def detect_gesture(self, frame_bgr: np.ndarray) -> Tuple[Optional[str], float, bool, bool]:
        """
        Detects hand gesture in a BGR frame.
        Returns (gesture_category, confidence_score, is_geometric_thumb_up, is_geometric_open_palm).
        """
        if self.recognizer is None:
            return None, 0.0, False, False

        try:
            import mediapipe as mp
            rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            result = self.recognizer.recognize(mp_image)

            top_gesture_name = None
            top_gesture_score = 0.0
            is_geom_thumb = False
            is_geom_palm = False

            if result.gestures and len(result.gestures) > 0:
                top_gesture = result.gestures[0][0]
                top_gesture_name = top_gesture.category_name
                top_gesture_score = top_gesture.score

            if result.hand_landmarks and len(result.hand_landmarks) > 0:
                for lm in result.hand_landmarks:
                    if len(lm) >= 21:
                        wrist = lm[0]
                        thumb_tip, thumb_ip, thumb_mcp = lm[4], lm[3], lm[2]
                        index_tip, index_pip, index_mcp = lm[8], lm[6], lm[5]
                        middle_tip, middle_pip, middle_mcp = lm[12], lm[10], lm[9]
                        ring_tip, ring_pip, ring_mcp = lm[16], lm[14], lm[13]
                        pinky_tip, pinky_pip, pinky_mcp = lm[20], lm[18], lm[17]

                        def dist_sq(p1, p2):
                            return (p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2

                        # Folded fingers check: Tips are closer to wrist or below MCP/PIP
                        index_folded = dist_sq(index_tip, wrist) < dist_sq(index_pip, wrist) * 1.15 or dist_sq(index_tip, index_mcp) < dist_sq(index_pip, index_mcp)
                        middle_folded = dist_sq(middle_tip, wrist) < dist_sq(middle_pip, wrist) * 1.15 or dist_sq(middle_tip, middle_mcp) < dist_sq(middle_pip, middle_mcp)
                        ring_folded = dist_sq(ring_tip, wrist) < dist_sq(ring_pip, wrist) * 1.15 or dist_sq(ring_tip, ring_mcp) < dist_sq(ring_pip, ring_mcp)
                        pinky_folded = dist_sq(pinky_tip, wrist) < dist_sq(pinky_pip, wrist) * 1.15 or dist_sq(pinky_tip, pinky_mcp) < dist_sq(pinky_pip, pinky_mcp)

                        folded_count = sum([index_folded, middle_folded, ring_folded, pinky_folded])

                        # Thumb extended & pointing upward/outward
                        thumb_extended = dist_sq(thumb_tip, wrist) > dist_sq(thumb_mcp, wrist) * 1.05
                        thumb_above_mcp = (thumb_tip.y < thumb_mcp.y) or (dist_sq(thumb_tip, index_tip) > dist_sq(thumb_mcp, index_mcp) * 1.1)

                        if folded_count >= 3 and thumb_extended and thumb_above_mcp:
                            is_geom_thumb = True

                        # Open Palm geometric check: at least 4 fingers extended away from wrist and MCP
                        index_ext = dist_sq(index_tip, wrist) > dist_sq(index_pip, wrist) * 1.1 and dist_sq(index_tip, wrist) > dist_sq(index_mcp, wrist) * 1.2
                        middle_ext = dist_sq(middle_tip, wrist) > dist_sq(middle_pip, wrist) * 1.1 and dist_sq(middle_tip, wrist) > dist_sq(middle_mcp, wrist) * 1.2
                        ring_ext = dist_sq(ring_tip, wrist) > dist_sq(ring_pip, wrist) * 1.1 and dist_sq(ring_tip, wrist) > dist_sq(ring_mcp, wrist) * 1.2
                        pinky_ext = dist_sq(pinky_tip, wrist) > dist_sq(pinky_pip, wrist) * 1.1 and dist_sq(pinky_tip, wrist) > dist_sq(pinky_mcp, wrist) * 1.2

                        extended_count = sum([index_ext, middle_ext, ring_ext, pinky_ext])
                        if extended_count >= 4 and thumb_extended:
                            is_geom_palm = True

                        if is_geom_thumb or is_geom_palm:
                            break

            return top_gesture_name, top_gesture_score, is_geom_thumb, is_geom_palm
        except Exception as e:
            logger.debug(f"Gesture error: {e}")

        return None, 0.0, False, False

    def is_thumb_up(self, frame_bgr: np.ndarray, min_score: float = 0.35) -> bool:
        """Returns True if a Thumb_Up gesture is detected."""
        gesture, score, is_geom_thumb, _ = self.detect_gesture(frame_bgr)
        return (gesture == "Thumb_Up" and score >= min_score) or is_geom_thumb

    def is_open_palm(self, frame_bgr: np.ndarray, min_score: float = 0.35) -> bool:
        """Returns True if an Open_Palm (🖐️) gesture is detected."""
        gesture, score, _, is_geom_palm = self.detect_gesture(frame_bgr)
        return (gesture == "Open_Palm" and score >= min_score) or is_geom_palm

    def is_gesture_valid(self, frame_bgr: np.ndarray, mode: str = "thumb_up", min_score: float = 0.35) -> Tuple[bool, Optional[str]]:
        """
        Validates gesture against requested mode: 'thumb_up', 'open_palm', or 'both'/'any'.
        Returns (is_valid, detected_gesture_name).
        """
        gesture, score, is_geom_thumb, is_geom_palm = self.detect_gesture(frame_bgr)
        thumb_ok = (gesture == "Thumb_Up" and score >= min_score) or is_geom_thumb
        palm_ok = (gesture == "Open_Palm" and score >= min_score) or is_geom_palm

        mode_clean = str(mode).lower().strip()
        if mode_clean in ("thumb_up", "thumbs_up", "pulgar", "pulgar_arriba"):
            return thumb_ok, ("Pulgar Arriba (👍)" if thumb_ok else None)
        elif mode_clean in ("open_palm", "palm", "mano_abierta", "mano"):
            return palm_ok, ("Mano Abierta (🖐️)" if palm_ok else None)
        elif mode_clean in ("both", "any", "all", "ambos"):
            if thumb_ok:
                return True, "Pulgar Arriba (👍)"
            if palm_ok:
                return True, "Mano Abierta (🖐️)"
            return False, None
        return thumb_ok, ("Pulgar Arriba (👍)" if thumb_ok else None)
