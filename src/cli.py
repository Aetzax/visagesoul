#!/usr/bin/env python3
"""
VisageSoul CLI: Command line interface for biometric facial and gestural authentication.
"""

import sys
import os
import time
import getpass
import argparse
import subprocess
import shutil
import json
from pathlib import Path
import cv2
import numpy as np

current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir.parent))

from src.config import config
from src.utils import setup_logger, list_video_devices, open_camera, warmup_camera, play_chime
from src.engine import FaceEngine, GestureEngine
from src.pam_manager import PamManager, SUPPORTED_SERVICES

logger = setup_logger("visagesoul-cli")


def ensure_root_privileges(action_name: str, service: str = ""):
    """If running as non-root, attempts sudo re-execution or shows helpful instructions."""
    if os.geteuid() != 0:
        print(f"\033[1;33m[Aviso] Se requieren permisos de administrador (sudo) para esta acción.\033[0m")
        try:
            cmd = ["sudo", sys.executable] + sys.argv
            return subprocess.call(cmd)
        except Exception:
            print(f"\033[1;31mError:\033[0m Ejecuta manualmente: \033[1;36msudo visagesoul {action_name} {service}\033[0m\n")
            return 1
    return None


def cmd_enroll(args):
    """Interactive enrollment of a user's face."""
    username = args.user or os.environ.get("SUDO_USER") or getpass.getuser()
    elevated = ensure_root_privileges("enroll", username)
    if elevated is not None:
        return elevated

    print(f"\n=======================================================")
    print(f"   📷 VisageSoul: Asistente de Registro Facial")
    print(f"   Usuario objetivo: \033[1;32m{username}\033[0m")
    print(f"=======================================================\n")

    try:
        engine = FaceEngine()
    except Exception as e:
        print(f"\033[1;31mError al inicializar el motor de reconocimiento:\033[0m {e}")
        return 1

    device_path = config.get("camera", "device", "/dev/video0")
    width = config.getint("camera", "width", 1280)
    height = config.getint("camera", "height", 720)
    fourcc = config.get("camera", "fourcc", "MJPG")
    fps = config.getint("camera", "fps", 30)

    print(f"Abriendo cámara: \033[1;36m{device_path}\033[0m ({width}x{height})...")
    cap = open_camera(device_path, width, height, fourcc, fps)
    if not cap:
        print(f"\033[1;31mError:\033[0m No se pudo abrir la cámara {device_path}.")
        return 1

    warmup_camera(cap, 5)

    SAMPLES_NEEDED = args.samples or 12
    collected_embeddings = []

    label = getattr(args, "label", None) or "Principal"
    print(f"\nIniciando captura de rostro para \033[1;32m{username}\033[0m [Aspecto: \033[1;36m{label}\033[0m]...")
    print("\nInstrucciones:")
    print("1. Mira fijamente a la cámara.")
    print("2. Gira suavemente la cabeza hacia la izquierda y derecha.")
    print("3. Cambia levemente de expresión (neutro, sonrisa).")
    print("\nPresiona \033[1;31m'q'\033[0m o Escape para cancelar.\n")

    window_name = f"VisageSoul - Registro Facial: {username} ({label})"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 800, 480)

    last_capture_time = 0
    capture_interval = 0.4

    while len(collected_embeddings) < SAMPLES_NEEDED:
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        display_frame = cv2.flip(frame, 1)
        raw_frame = frame

        faces = engine.detect_faces(raw_frame)
        primary_face = engine.get_primary_face(faces)

        h, w, _ = display_frame.shape
        progress_pct = int((len(collected_embeddings) / SAMPLES_NEEDED) * 100)

        cv2.rectangle(display_frame, (0, 0), (w, 60), (30, 30, 30), -1)
        cv2.putText(
            display_frame,
            f"VisageSoul - {label}: {len(collected_embeddings)}/{SAMPLES_NEEDED} ({progress_pct}%)",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85,
            (0, 255, 128),
            2,
        )

        if primary_face is not None:
            bx, by, bw, bh = int(primary_face[0]), int(primary_face[1]), int(primary_face[2]), int(primary_face[3])
            mirrored_bx = w - (bx + bw)
            cv2.rectangle(display_frame, (mirrored_bx, by), (mirrored_bx + bw, by + bh), (0, 255, 0), 2)
            cv2.putText(
                display_frame,
                "Rostro Detectado",
                (mirrored_bx, max(20, by - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

            current_time = time.time()
            if current_time - last_capture_time >= capture_interval:
                emb = engine.extract_embedding(raw_frame, primary_face)
                collected_embeddings.append(emb)
                last_capture_time = current_time
                print(f"  [+] Muestra {len(collected_embeddings)}/{SAMPLES_NEEDED} capturada exitosamente.")
        else:
            cv2.putText(
                display_frame,
                "Buscando rostro...",
                (20, h - 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 165, 255),
                2,
            )

        cv2.imshow(window_name, display_frame)
        key = cv2.waitKey(1) & 0xFF
        if key in [ord('q'), ord('Q'), 27] or cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            print("\n\033[1;33mRegistro cancelado por el usuario.\033[0m")
            cap.release()
            cv2.destroyAllWindows()
            return 1

    cap.release()
    cv2.destroyAllWindows()

    print(f"\nGuardando aspecto '{label}' en el perfil de {username}...")
    success = engine.save_profile(username, collected_embeddings, label=label, append=True, metadata={"camera": device_path})
    if success:
        print(f"\033[1;32m¡Éxito!\033[0m El aspecto '\033[1;36m{label}\033[0m' para \033[1;32m{username}\033[0m ha sido guardado correctamente.")
        print(f"Ubicación: {engine.get_profile_path(username)}\n")
        play_chime("match")
        return 0
    else:
        print(f"\033[1;31mError:\033[0m No se pudo guardar el perfil en disco.")
        return 1


def cmd_test(args):
    """Live camera, recognition and gesture test."""
    username = args.user or getpass.getuser()
    print(f"\n=======================================================")
    print(f"   👁️  VisageSoul: Probador de Reconocimiento y Gestos")
    print(f"   Verificando contra: \033[1;32m{username}\033[0m")
    print(f"=======================================================\n")

    try:
        engine = FaceEngine()
        gesture_engine = GestureEngine()
    except Exception as e:
        print(f"\033[1;31mError al inicializar el motor:\033[0m {e}")
        return 1

    user_embeddings = engine.load_profile(username)
    if not user_embeddings:
        print(f"\033[1;33mAdvertencia:\033[0m No hay perfil registrado para '{username}'.")
        print("Registra tu rostro primero con: \033[1;36mvisagesoul enroll\033[0m\n")

    device_path = config.get("camera", "device", "/dev/video0")
    threshold = config.getfloat("security", "threshold", 0.70)
    require_gesture = config.getboolean("security", "require_gesture", config.getboolean("security", "require_thumbs_up", False))
    gesture_mode = config.get("security", "gesture_type", "thumb_up").lower()
    cap = open_camera(device_path)
    if not cap:
        print(f"\033[1;31mError:\033[0m No se pudo abrir {device_path}.")
        return 1

    warmup_camera(cap, 5)
    window_name = "VisageSoul - Probador en Vivo (Presiona 'q' para salir)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 540)

    print("Mostrando feed de cámara. Presiona 'q' en la ventana para salir.\n")

    face_history = []
    liveness_check = config.getboolean("security", "liveness_check", True)
    consecutive_test_matches = 0

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        raw_frame = frame.copy()
        display_frame = cv2.flip(frame, 1)
        h, w, _ = display_frame.shape

        faces = engine.detect_faces(raw_frame)
        primary_face = engine.get_primary_face(faces)
        gesture_name, gesture_score, is_geom_thumb, is_geom_palm, _ = gesture_engine.detect_gesture(raw_frame)
        gesture_valid, valid_gesture_name = gesture_engine.is_gesture_valid(raw_frame, mode=gesture_mode, primary_face=primary_face)

        cv2.rectangle(display_frame, (0, 0), (w, 55), (20, 20, 20), -1)

        if primary_face is not None:
            bx, by, bw, bh = int(primary_face[0]), int(primary_face[1]), int(primary_face[2]), int(primary_face[3])
            mirrored_bx = w - (bx + bw)

            liveness_ok = True
            liveness_msg = "Rostro 3D Vivo"
            if liveness_check:
                liveness_ok, liveness_val, liveness_msg = engine.check_liveness(raw_frame, primary_face)

            score_text = "Sin perfil cargado"
            box_color = (255, 255, 0)
            bar_color = (30, 30, 30)

            if user_embeddings:
                target_emb = engine.extract_embedding(raw_frame, primary_face)
                is_match, score = engine.verify_against_profile(target_emb, user_embeddings, threshold=threshold)
                pct = int(score * 100)

                if is_match and not liveness_ok:
                    consecutive_test_matches = 0
                    box_color = (0, 0, 255)
                    bar_color = (20, 20, 180)
                    score_text = f"[⛔ DENEGADO / FOTO] {liveness_msg}"
                elif is_match and liveness_ok:
                    if require_gesture:
                        if gesture_valid:
                            consecutive_test_matches += 1
                            if consecutive_test_matches >= 5:
                                box_color = (0, 255, 0)
                                bar_color = (20, 140, 20)
                                clean_gesture_name = "Pulgar Arriba (👍)" if "Pulgar" in str(valid_gesture_name) else ("Mano Abierta (🖐️)" if "Mano" in str(valid_gesture_name) else str(valid_gesture_name))
                                score_text = f"[✓ AUTORIZADO] {username} ({pct}%) + {clean_gesture_name}"
                            else:
                                box_color = (0, 255, 200)
                                bar_color = (0, 100, 140)
                                score_text = f"[⏳ VALIDANDO] Mantén el gesto ({consecutive_test_matches}/5)..."
                        else:
                            consecutive_test_matches = 0
                            box_color = (0, 165, 255)
                            bar_color = (0, 80, 160)
                            hint = "Pulgar (👍) o Mano (🖐️)" if gesture_mode == "both" else ("Mano Abierta (🖐️)" if gesture_mode == "open_palm" else "Pulgar Arriba (👍)")
                            score_text = f"[✋ GESTO REQUERIDO] Muestra {hint}"
                    else:
                        consecutive_test_matches += 1
                        if consecutive_test_matches >= 5:
                            box_color = (0, 255, 0)
                            bar_color = (20, 140, 20)
                            score_text = f"[✓ AUTORIZADO] {username} ({pct}% similitud)"
                        else:
                            box_color = (0, 255, 200)
                            bar_color = (0, 100, 140)
                            score_text = f"[⏳ VALIDANDO] Verificando estabilidad ({consecutive_test_matches}/5)..."
                else:
                    consecutive_test_matches = 0
                    box_color = (0, 0, 255)
                    bar_color = (20, 20, 140)
                    score_text = f"[X NO COINCIDE] ({pct}% / req {int(threshold*100)}%)"

            cv2.rectangle(display_frame, (0, 0), (w, 60), bar_color, -1)
            cv2.putText(display_frame, score_text, (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2)
            cv2.rectangle(display_frame, (mirrored_bx, by), (mirrored_bx + bw, by + bh), box_color, 2)
        else:
            consecutive_test_matches = 0
            engine.antispoof.reset()
            gesture_engine.reset()
            cv2.rectangle(display_frame, (0, 0), (w, 60), (40, 40, 40), -1)
            cv2.putText(display_frame, "Buscando rostro...", (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (180, 180, 180), 2)

        # Draw Real-time Telemetry HUD at the bottom
        metrics = engine.get_last_antispoof_metrics()
        p_real = metrics.get("p_real", 0.0)
        p_screen = metrics.get("p_screen", 0.0)
        rigidity = metrics.get("rigidity_score", 0.0)
        eye_std = metrics.get("eye_std", 0.0)

        cv2.rectangle(display_frame, (0, h - 55), (w, h), (15, 15, 15), -1)
        hud_line1 = f"IA Anti-Spoof: Real {p_real*100:.0f}% | Pantalla {p_screen*100:.0f}% | Rigidez 3D: {rigidity:.5f} (req >= 0.012)"
        hud_line2 = f"Dinamica Ocular: {eye_std:.5f} (req >= 0.001) | Consenso: {consecutive_test_matches}/5 | Gesto: {gesture_name}"
        cv2.putText(display_frame, hud_line1, (15, h - 32), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        cv2.putText(display_frame, hud_line2, (15, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 200) if gesture_valid else (180, 180, 180), 1)

        cv2.imshow(window_name, display_frame)
        key = cv2.waitKey(1) & 0xFF
        if key in [ord('r'), ord('R')]:
            engine.antispoof.reset()
            gesture_engine.reset()
            consecutive_test_matches = 0
        elif key in [ord('q'), ord('Q'), 27] or cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break

    cap.release()
    cv2.destroyAllWindows()
    return 0


def cmd_list(args):
    """Lists enrolled face profiles and sub-models."""
    engine = FaceEngine()
    users = engine.list_enrolled_users()

    print("\n--- Perfiles Faciales Registrados en VisageSoul ---")
    if not users:
        print("No hay ningún usuario registrado actualmente.")
    else:
        for u in users:
            print(f" • \033[1;32m{u['username']}\033[0m ({u['sample_count']} muestras totales):")
            for m in u.get("models", []):
                print(f"    └── 🏷️  \033[1;36m{m.get('name', 'Principal')}\033[0m: {m.get('sample_count', '?')} muestras ({m.get('created_at', '')[:10]})")
    print("")
    return 0


def cmd_remove(args):
    """Deletes an enrolled face profile."""
    username = args.user
    if not username:
        print("Error: Debes especificar el nombre de usuario.")
        return 1

    elevated = ensure_root_privileges("remove", username)
    if elevated is not None:
        return elevated

    engine = FaceEngine()
    if engine.delete_profile(username):
        print(f"\033[1;32mPerfil para '{username}' eliminado correctamente.\033[0m")
        return 0
    else:
        print(f"\033[1;31mError:\033[0m No se encontró o no se pudo eliminar el perfil de '{username}'.")
        return 1


def cmd_save_profile(args):
    """Saves a profile from a temporary file with root privileges (internal / GUI helper)."""
    if os.geteuid() != 0:
        print("Error: Se requieren permisos de administrador (root) para guardar perfiles faciales.", file=sys.stderr)
        return 1
    username = args.user
    temp_file = Path(args.file)
    if not temp_file.is_file():
        print(f"Error: Archivo temporal {temp_file} no encontrado.", file=sys.stderr)
        return 1
    try:
        with open(temp_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        label = data.get("label", "Principal")
        embeddings = [np.array(e, dtype=np.float32) for e in data.get("embeddings", [])]
        engine = FaceEngine()
        success = engine.save_profile(username, embeddings, label=label, append=True, metadata=data.get("metadata", {}))
        try:
            temp_file.unlink()
        except Exception:
            pass
        if success:
            print(f"Aspecto '{label}' para {username} guardado exitosamente.")
            return 0
        else:
            print(f"Error: No se pudo escribir el perfil facial para {username}.", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error al guardar el perfil: {e}", file=sys.stderr)
        return 1


def cmd_status(args):
    """Displays comprehensive status of VisageSoul components."""
    print("\n=======================================================")
    print("   📊 Estado General de VisageSoul")
    print("=======================================================")

    dev = config.get("camera", "device", "/dev/video0")
    dev_exists = os.path.exists(dev)
    print(f"\nCámara: {dev} -> " + ("\033[1;32m[CONECTADA]\033[0m" if dev_exists else "\033[1;31m[DESCONECTADA]\033[0m"))

    pam = PamManager()
    mod_installed = pam.is_module_installed()
    print(f"Módulo PAM: " + ("\033[1;32m[INSTALADO]\033[0m" if mod_installed else "\033[1;31m[NO INSTALADO]\033[0m"))

    thumbs = config.getboolean("security", "require_thumbs_up", False)
    print(f"Modo Gesto Pulgar Arriba (👍): " + ("\033[1;32m[ACTIVADO]\033[0m" if thumbs else "\033[1;30m[DESACTIVADO]\033[0m"))

    auto_unl = config.getboolean("security", "auto_unlock", True)
    print(f"Desbloqueo Instantáneo: " + ("\033[1;32m[ACTIVADO]\033[0m" if auto_unl else "\033[1;30m[DESACTIVADO]\033[0m"))

    print("\nIntegraciones PAM:")
    statuses = pam.get_all_statuses()
    for svc, st in statuses.items():
        if not st["exists"]:
            print(f"  • {svc:<14}: \033[1;30m[NO PRESENTE EN SISTEMA]\033[0m")
        elif st["enabled"]:
            print(f"  • {svc:<14}: \033[1;32m[ACTIVO / HABILITADO]\033[0m")
        else:
            print(f"  • {svc:<14}: \033[1;33m[DESACTIVADO]\033[0m")

    engine = FaceEngine()
    users = engine.list_enrolled_users()
    print(f"\nUsuarios registrados: {len(users)}")
    for u in users:
        print(f"  - {u['username']} ({u['sample_count']} muestras)")
    print("")
    return 0


def cmd_enable(args):
    """Enables PAM integration for a service."""
    elevated = ensure_root_privileges("enable", args.service)
    if elevated is not None:
        return elevated

    service = args.service
    pam = PamManager()

    if service == "all":
        services_to_enable = ["sddm", "kde", "sudo", "polkit-1"]
    else:
        services_to_enable = [service]

    for svc in services_to_enable:
        ok, msg = pam.enable_service(svc)
        if ok:
            print(f"\033[1;32m[OK]\033[0m {msg}")
        else:
            print(f"\033[1;31m[ERROR]\033[0m {msg}")
    return 0


def cmd_disable(args):
    """Disables PAM integration for a service."""
    elevated = ensure_root_privileges("disable", args.service)
    if elevated is not None:
        return elevated

    service = args.service
    pam = PamManager()

    if service == "all":
        services_to_disable = ["sddm", "kde", "sudo", "polkit-1", "system-auth", "system-login"]
    else:
        services_to_disable = [service]

    for svc in services_to_disable:
        ok, msg = pam.disable_service(svc)
        if ok:
            print(f"\033[1;32m[OK]\033[0m {msg}")
        else:
            print(f"\033[1;31m[ERROR]\033[0m {msg}")
    return 0


def cmd_apply_pam(args):
    """Applies bulk PAM configuration changes (invoked by GUI/Polkit)."""
    pam = PamManager()
    services = {
        "sddm": args.sddm,
        "kde": args.kde,
        "sudo": args.sudo,
        "polkit-1": args.polkit,
    }

    results = []
    for svc, state in services.items():
        if state == "on":
            ok, msg = pam.enable_service(svc)
            results.append(f"[VisageSoul] {svc}: {'OK' if ok else 'FAIL'} - {msg}")
        elif state == "off":
            ok, msg = pam.disable_service(svc)
            results.append(f"[VisageSoul] {svc}: {'OK' if ok else 'FAIL'} - {msg}")

    if hasattr(args, "bypass_welcome") and args.bypass_welcome != "ignore":
        if args.bypass_welcome == "on":
            ok, msg = pam.set_bypass_welcome_page(True)
            results.append(f"[VisageSoul] bypass-welcome: {'OK' if ok else 'FAIL'} - {msg}")
        elif args.bypass_welcome == "off":
            ok, msg = pam.set_bypass_welcome_page(False)
            results.append(f"[VisageSoul] bypass-welcome: {'OK' if ok else 'FAIL'} - {msg}")

    print("\n".join(results))
    return 0


def cmd_uninstall(args):
    """Safely uninstalls VisageSoul from the system."""
    elevated = ensure_root_privileges("uninstall", "")
    if elevated is not None:
        return elevated

    print("\n=======================================================")
    print("   🗑️  Desinstalador de VisageSoul")
    print("=======================================================\n")

    pam = PamManager()
    print("1. Desactivando reglas de inicio de sesión en PAM...")
    for svc in SUPPORTED_SERVICES:
        pam.disable_service(svc)

    print("2. Desactivando cualquier bypass de pantalla de bienvenida (Autologin)...")
    pam.set_bypass_welcome_page(False)
    for home_user in Path("/home").glob("*"):
        autostart = home_user / ".config" / "autostart" / "visagesoul-startup-lock.desktop"
        if autostart.is_file():
            try:
                autostart.unlink()
            except Exception:
                pass

    print("3. Eliminando módulos del sistema...")
    paths_to_remove = [
        "/usr/lib/security/pam_visagesoul.so",
        "/usr/lib/security/pam_aura_auth.so",
        "/usr/local/bin/visagesoul",
        "/usr/local/bin/visagesoul-verify",
        "/usr/local/bin/aura",
        "/usr/local/bin/aura-verify",
        "/usr/share/applications/visagesoul.desktop",
        "/usr/share/applications/aura-auth.desktop",
        "/usr/share/polkit-1/actions/org.visagesoul.policy",
        "/usr/share/polkit-1/actions/org.auraauth.policy",
        "/usr/share/visagesoul",
        "/opt/visagesoul",
        "/opt/aura-auth",
    ]

    for p in paths_to_remove:
        path = Path(p)
        if path.is_file() or path.is_symlink():
            try:
                path.unlink()
                print(f"  ✓ Eliminado archivo: {p}")
            except Exception as e:
                print(f"  ⚠ No se pudo eliminar {p}: {e}")
        elif path.is_dir():
            try:
                shutil.rmtree(path)
                print(f"  ✓ Eliminada carpeta: {p}")
            except Exception as e:
                print(f"  ⚠ No se pudo eliminar carpeta {p}: {e}")

    if getattr(args, "purge", False):
        print("3. Purgando perfiles biométricos...")
        for p in ["/etc/visagesoul", "/etc/aura-auth"]:
            path = Path(p)
            if path.is_dir():
                shutil.rmtree(path)
                print(f"  ✓ Eliminados datos en: {p}")
    else:
        print("3. Conservando perfiles en /etc/visagesoul/faces por seguridad.")

    print("\n\033[1;32m✓ VisageSoul ha sido desinstalado completamente con éxito.\033[0m\n")
    return 0


def cmd_doctor(args):
    """Self-diagnostic tool to verify system health and troubleshoot."""
    print("\n=======================================================")
    print("   🩺 VisageSoul Doctor - Diagnóstico del Sistema")
    print("=======================================================")

    issues_found = 0

    print("\n1. Verificando librerías del sistema...")
    try:
        import cv2
        print(f"   ✓ OpenCV: {cv2.__version__}")
    except ImportError:
        print("   ✗ OpenCV no disponible.")
        issues_found += 1

    try:
        import numpy as np
        print(f"   ✓ NumPy: {np.__version__}")
    except ImportError:
        print("   ✗ NumPy no disponible.")
        issues_found += 1

    try:
        import mediapipe as mp
        print(f"   ✓ MediaPipe (Gestos): {mp.__version__}")
    except ImportError:
        print("   ⚠ MediaPipe no instalado (detección de pulgar arriba no disponible).")

    print("\n2. Verificando modelos neuronales de IA...")
    models_dir = Path(config.get("paths", "models_dir"))
    yunet = models_dir / "face_detection_yunet_2023mar.onnx"
    sface = models_dir / "face_recognition_sface_2021dec.onnx"
    gesture = models_dir / "gesture_recognizer.task"

    if yunet.is_file():
        print(f"   ✓ YuNet (Detector): Presente")
    else:
        print(f"   ✗ YuNet no encontrado en {yunet}")
        issues_found += 1

    if sface.is_file():
        print(f"   ✓ SFace (Reconocedor): Presente")
    else:
        print(f"   ✗ SFace no encontrado en {sface}")
        issues_found += 1

    if gesture.is_file():
        print(f"   ✓ MediaPipe Gesture Recognizer (👍): Presente")
    else:
        print(f"   ⚠ Gesture Recognizer no encontrado.")

    print("\n3. Verificando cámara Logitech StreamCam...")
    dev_path = config.get("camera", "device", "/dev/video0")
    if os.path.exists(dev_path):
        print(f"   ✓ Dispositivo {dev_path} conectado.")
        cap = open_camera(dev_path)
        if cap and cap.isOpened():
            print("   ✓ Transmisión V4L2 operativa.")
            cap.release()
        else:
            print(f"   ✗ Cámara ocupada o inaccesible.")
            issues_found += 1
    else:
        print(f"   ✗ {dev_path} no encontrado.")
        issues_found += 1

    print("\n4. Verificando módulo PAM...")
    pam = PamManager()
    if pam.is_module_installed():
        print("   ✓ pam_visagesoul.so instalado en biblioteca de seguridad.")
    else:
        print("   ⚠ pam_visagesoul.so no instalado.")

    print("\n-------------------------------------------------------")
    if issues_found == 0:
        print("\033[1;32m✓ VisageSoul está en perfecto estado y listo para usar.\033[0m\n")
        return 0
    else:
        print(f"\033[1;31m✗ Se detectaron {issues_found} problemas.\033[0m\n")
        return 1


def cmd_gui(args):
    """Launches the Qt6 graphical configurator."""
    try:
        from src.gui import launch_gui
        return launch_gui()
    except ImportError as e:
        print(f"\033[1;31mError al iniciar la interfaz gráfica:\033[0m {e}")
        return 1


def print_custom_help():
    """Prints a beautiful, human-readable colorful CLI help menu."""
    print(r"""
\033[1;34m  _   _ _                        ____              _ 
 | | | (_)___  __ _  __ _  ___  / ___|  ___  _   _| |
 | | | | / __|/ _` |/ _` |/ _ \ \___ \ / _ \| | | | |
  \ V /| \__ \ (_| | (_| |  __/  ___) | (_) | |_| | |
   \_/ |_|___/\__,_|\__, |\___| |____/ \___/ \__,_|_|
                    |___/                            \033[0m
 \033[1;36m✨ VisageSoul v1.0.0 (Build 2026.08.31) — Biometría Facial & Gestual para Linux\033[0m
 \033[1;30m🌐 GitHub:\033[0m \033[4;34mhttps://github.com/Aetzax/visagesoul\033[0m  |  \033[1;35mDonaciones:\033[0m \033[4;35mhttps://paypal.me/aetzax1\033[0m

\033[1;33mUso:\033[0m \033[1mvisagesoul <comando> [opciones]\033[0m

\033[1;32mComandos Principales:\033[0m
  \033[1;36mgui\033[0m                    Abrir el panel de control gráfico Qt6
  \033[1;36menroll\033[0m [usuario]       Registrar un nuevo rostro o aspecto facial
  \033[1;36mtest\033[0m [usuario]         Probar la cámara y gestos en vivo
  \033[1;36mstatus\033[0m                 Mostrar estado del sistema, cámara y PAM
  \033[1;36mdoctor\033[0m                 Diagnóstico de librerías, hardware y permisos
  \033[1;36mlist\033[0m                   Listar perfiles y aspectos biométricos registrados
  \033[1;36mremove\033[0m <usuario>       Eliminar el perfil biométrico de un usuario

\033[1;32mGestión de Seguridad & PAM:\033[0m
  \033[1;36menable\033[0m <servicio>      Activar en: \033[1mkde, sddm, sudo, polkit-1, all\033[0m
  \033[1;36mdisable\033[0m <servicio>     Desactivar en un servicio específico
  \033[1;36muninstall\033[0m              Desinstalar VisageSoul del sistema limpiamente

\033[1;32mOpciones Globales:\033[0m
  \033[1;36m-h, --help\033[0m             Mostrar esta ayuda detallada
  \033[1;36m-v, --version\033[0m          Mostrar versión del sistema

\033[1;33mEjemplos Rápidos:\033[0m
  visagesoul gui                        \033[1;30m# Abre el configurador visual\033[0m
  visagesoul enroll aetzax              \033[1;30m# Registra tu rostro\033[0m
  visagesoul enroll --label "Con gafas" \033[1;30m# Registra un nuevo aspecto\033[0m
  visagesoul enable all                 \033[1;30m# Activa biometría en todo el sistema\033[0m
  visagesoul test                       \033[1;30m# Prueba la detección en tiempo real\033[0m
""")


def main():
    if len(sys.argv) == 1 or sys.argv[1] in ("-h", "--help", "help"):
        print_custom_help()
        sys.exit(0)

    if sys.argv[1] in ("-v", "--version", "version"):
        print("\033[1;36mVisageSoul v1.0.0 (Build 2026.08.31)\033[0m")
        print("https://github.com/Aetzax/visagesoul")
        sys.exit(0)

    parser = argparse.ArgumentParser(prog="visagesoul", description="VisageSoul Biometric Authentication Management Tool", add_help=False)
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # enroll
    p_enroll = subparsers.add_parser("enroll", help="Registrar rostro de un usuario")
    p_enroll.add_argument("user", nargs="?", default=None, help="Nombre de usuario")
    p_enroll.add_argument("--label", "-l", default="Principal", help="Etiqueta del aspecto (ej: 'Con gafas', 'Sin gafas', 'Principal')")
    p_enroll.add_argument("--samples", "-s", type=int, default=12, help="Número de muestras a capturar")
    p_enroll.set_defaults(func=cmd_enroll)

    # test
    p_test = subparsers.add_parser("test", help="Probar reconocimiento en vivo y gestos")
    p_test.add_argument("user", nargs="?", default=None, help="Nombre de usuario")
    p_test.set_defaults(func=cmd_test)

    # list
    p_list = subparsers.add_parser("list", help="Listar usuarios registrados")
    p_list.set_defaults(func=cmd_list)

    # remove
    p_remove = subparsers.add_parser("remove", help="Eliminar perfil de usuario")
    p_remove.add_argument("user", help="Nombre de usuario a eliminar")
    p_remove.set_defaults(func=cmd_remove)

    # status
    p_status = subparsers.add_parser("status", help="Mostrar estado de la cámara y servicios PAM")
    p_status.set_defaults(func=cmd_status)

    # enable
    p_enable = subparsers.add_parser("enable", help="Activar en un servicio PAM")
    p_enable.add_argument("service", choices=["sddm", "kde", "sudo", "polkit-1", "all"], help="Servicio")
    p_enable.set_defaults(func=cmd_enable)

    # disable
    p_disable = subparsers.add_parser("disable", help="Desactivar en un servicio PAM")
    p_disable.add_argument("service", choices=["sddm", "kde", "sudo", "polkit-1", "system-auth", "system-login", "all"], help="Servicio")
    p_disable.set_defaults(func=cmd_disable)

    # uninstall
    p_uninst = subparsers.add_parser("uninstall", help="Desinstalar VisageSoul del sistema")
    p_uninst.add_argument("-y", "--yes", action="store_true", help="Confirmar desinstalación sin preguntar")
    p_uninst.add_argument("--purge", action="store_true", help="Eliminar también los perfiles faciales")
    p_uninst.set_defaults(func=cmd_uninstall)

    # apply-pam (internal / Polkit)
    p_apply = subparsers.add_parser("apply-pam", help="Aplicar estados de PAM en bloque")
    p_apply.add_argument("--sddm", choices=["on", "off", "ignore"], default="ignore")
    p_apply.add_argument("--kde", choices=["on", "off", "ignore"], default="ignore")
    p_apply.add_argument("--sudo", choices=["on", "off", "ignore"], default="ignore")
    p_apply.add_argument("--polkit", choices=["on", "off", "ignore"], default="ignore")
    p_apply.add_argument("--bypass-welcome", choices=["on", "off", "ignore"], default="ignore")
    p_apply.set_defaults(func=cmd_apply_pam)

    # save-profile (internal / GUI)
    p_save_prof = subparsers.add_parser("save-profile", help="Guardar perfil facial")
    p_save_prof.add_argument("--user", "-u", required=True, help="Nombre de usuario")
    p_save_prof.add_argument("--file", "-f", required=True, help="Archivo temporal")
    p_save_prof.set_defaults(func=cmd_save_profile)

    # doctor
    p_doctor = subparsers.add_parser("doctor", help="Comprobar salud y configuración")
    p_doctor.set_defaults(func=cmd_doctor)

    # gui
    p_gui = subparsers.add_parser("gui", help="Abrir el configurador visual Qt6")
    p_gui.set_defaults(func=cmd_gui)

    args = parser.parse_args()
    if not args.command:
        print_custom_help()
        sys.exit(0)

    exit_code = args.func(args)
    sys.exit(exit_code or 0)


if __name__ == "__main__":
    main()
