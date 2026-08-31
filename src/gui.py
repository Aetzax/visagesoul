"""
Qt6 GUI Configuration and Management Dashboard for VisageSoul.
Sleek, dark modern UI designed for KDE Plasma Tokyo Night environment.
Clean 4-tab architecture:
  1. 📊 Estado General (Overview)
  2. 📷 Registro Facial (Face Profiles & Aspects)
  3. 🛡️ Seguridad y PAM (Security & PAM Integration)
  4. ⚙️ Preferencias y Sistema (Preferences & System Maintenance)
"""

import sys
import os
import time
import getpass
import subprocess
import shutil
import json
import datetime
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap, QIcon, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QProgressBar, QCheckBox,
    QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox, QListWidget,
    QListWidgetItem, QMessageBox, QFileDialog, QLineEdit, QFormLayout,
    QInputDialog, QSlider
)

from .config import config
from .engine import FaceEngine, GestureEngine
from .pam_manager import PamManager
from .utils import list_video_devices, open_camera, play_chime
from .i18n import tr, get_current_language


DARK_KDE_STYLE = """
QMainWindow, QWidget {
    background-color: #1a1b26;
    color: #c0caf5;
    font-family: 'Segoe UI', 'Noto Sans', 'Inter', sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #2f354a;
    background-color: #16161e;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background: #1f2335;
    color: #7aa2f7;
    padding: 10px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #2f354a;
    margin-right: 4px;
    font-weight: bold;
}

QTabBar::tab:selected {
    background: #24283b;
    color: #7dcfff;
    border-bottom: 2px solid #7aa2f7;
}

QTabBar::tab:hover {
    background: #292e42;
    color: #bb9af7;
}

QGroupBox {
    border: 1px solid #2f354a;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 18px;
    font-weight: bold;
    color: #bb9af7;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #7aa2f7;
}

QPushButton {
    background-color: #24283b;
    border: 1px solid #3b4261;
    border-radius: 6px;
    color: #c0caf5;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #2f354a;
    border-color: #7aa2f7;
    color: #7dcfff;
}

QPushButton:pressed {
    background-color: #414868;
}

QPushButton#primaryBtn {
    background-color: #3d59a1;
    border: 1px solid #7aa2f7;
    color: #ffffff;
}

QPushButton#primaryBtn:hover {
    background-color: #4869bf;
}

QPushButton#dangerBtn {
    background-color: #992b45;
    border: 1px solid #f7768e;
    color: #ffffff;
}

QPushButton#dangerBtn:hover {
    background-color: #b83655;
}

QProgressBar {
    border: 1px solid #2f354a;
    border-radius: 6px;
    text-align: center;
    background-color: #1f2335;
    color: #c0caf5;
    font-weight: bold;
    height: 22px;
}

QProgressBar::chunk {
    background-color: #7aa2f7;
    border-radius: 5px;
}

QCheckBox {
    spacing: 8px;
    color: #c0caf5;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #3b4261;
    background-color: #1f2335;
}

QCheckBox::indicator:checked {
    background-color: #7aa2f7;
    border-color: #7dcfff;
}

QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background-color: #1f2335;
    border: 1px solid #3b4261;
    border-radius: 6px;
    padding: 6px 10px;
    color: #c0caf5;
}

QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:focus {
    border: 1px solid #7aa2f7;
}

QListWidget {
    background-color: #16161e;
    border: 1px solid #2f354a;
    border-radius: 6px;
    padding: 4px;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
}

QListWidget::item:selected {
    background-color: #24283b;
    color: #7dcfff;
    border: 1px solid #7aa2f7;
}

QSlider::groove:horizontal {
    border: 1px solid #2f354a;
    height: 8px;
    background: #1f2335;
    border-radius: 4px;
}

QSlider::sub-page:horizontal {
    background: #7aa2f7;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #7dcfff;
    border: 1px solid #3b4261;
    width: 18px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 9px;
}
"""


class CameraWorker(QThread):
    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self, device_path: str):
        super().__init__()
        self.device_path = device_path
        self.running = True

    def run(self):
        width = config.getint("camera", "width", 1280)
        height = config.getint("camera", "height", 720)
        fourcc = config.get("camera", "fourcc", "MJPG")
        fps = config.getint("camera", "fps", 30)

        cap = open_camera(self.device_path, width, height, fourcc, fps)
        if not cap:
            return

        while self.running:
            ret, frame = cap.read()
            if ret and frame is not None:
                self.frame_ready.emit(frame)
            time.sleep(0.03)

        cap.release()

    def stop(self):
        self.running = False
        self.wait()


def get_app_icon() -> QIcon:
    search_paths = [
        Path(__file__).resolve().parent.parent / "assets" / "visagesoul.svg",
        Path(__file__).resolve().parent.parent / "assets" / "visagesoul.png",
        Path("/usr/share/icons/hicolor/scalable/apps/visagesoul.svg"),
        Path("/usr/share/pixmaps/visagesoul.svg"),
        Path("/usr/share/pixmaps/visagesoul.png"),
        Path("/opt/visagesoul/assets/visagesoul.svg"),
        Path("/opt/visagesoul/assets/visagesoul.png"),
    ]
    for p in search_paths:
        if p.is_file():
            return QIcon(str(p))
    return QIcon.fromTheme("camera-web")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("app_title"))
        self.resize(900, 700)
        self.setStyleSheet(DARK_KDE_STYLE)
        self.setWindowIcon(get_app_icon())

        self.engine = FaceEngine()
        self.gesture_engine = GestureEngine()
        self.pam = PamManager()

        self.camera_worker = None
        self.enrolling = False
        self.enrolled_samples = []
        self.target_samples = 12
        self.last_capture_time = 0

        self.init_ui()

    def execute_elevated(self, args: List[str], prompt_title: str = "Permisos de Administrador", prompt_message: str = "Introduce la contraseña de sudo:") -> tuple[bool, str]:
        """Executes visagesoul CLI commands with elevated root permissions using pkexec or fallback Qt password dialog."""
        was_camera_running = False
        if self.camera_worker and self.camera_worker.isRunning():
            was_camera_running = True
            self.camera_worker.stop()
            time.sleep(0.15)

        # Set bypass environment so PAM never uses biometrics inside the GUI
        exec_env = os.environ.copy()
        exec_env["VISAGESOUL_NO_PAM"] = "1"

        try:
            if os.geteuid() == 0:
                cli_bin = str(Path(__file__).resolve().parent / "cli.py")
                res = subprocess.run([sys.executable, cli_bin] + args, capture_output=True, text=True, env=exec_env)
                return (res.returncode == 0, res.stdout or res.stderr)

            cli_bin = "/usr/local/bin/visagesoul"
            if not os.path.exists(cli_bin):
                cli_bin = str(Path(__file__).resolve().parent / "cli.py")
                cmd_base = [sys.executable, cli_bin]
            else:
                cmd_base = [cli_bin]

            # 1. Prompt user with native Qt Password Dialog
            password, ok = QInputDialog.getText(
                self,
                prompt_title,
                prompt_message,
                QLineEdit.EchoMode.Password
            )
            if not ok or not password:
                return False, "Operación cancelada por el usuario."

            sudo_cmd = ["sudo", "--preserve-env=VISAGESOUL_NO_PAM", "-S", "-p", ""] + cmd_base + args
            try:
                proc = subprocess.run(
                    sudo_cmd,
                    input=f"{password}\n",
                    capture_output=True,
                    text=True,
                    env=exec_env
                )
                if proc.returncode == 0:
                    return True, proc.stdout
                else:
                    return False, proc.stderr or proc.stdout or "Contraseña incorrecta."
            except Exception as e:
                return False, str(e)
        finally:
            if was_camera_running:
                self.start_camera_worker()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Header Banner
        header = QHBoxLayout()
        title_label = QLabel("✨ VisageSoul")
        title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #7aa2f7;")
        subtitle = QLabel(tr("app_subtitle"))
        subtitle.setStyleSheet("color: #565f89; font-size: 13px; margin-left: 10px;")

        header.addWidget(title_label)
        header.addWidget(subtitle)
        header.addStretch()
        main_layout.addLayout(header)

        # 4 Clean Tabs
        self.tabs = QTabWidget()
        self.tab_dashboard = QWidget()
        self.tab_enroll = QWidget()
        self.tab_security = QWidget()
        self.tab_preferences = QWidget()

        self.tabs.addTab(self.tab_dashboard, tr("tab_dashboard"))
        self.tabs.addTab(self.tab_enroll, tr("tab_enroll"))
        self.tabs.addTab(self.tab_security, tr("tab_security"))
        self.tabs.addTab(self.tab_preferences, tr("tab_preferences"))

        main_layout.addWidget(self.tabs)

        self.setup_dashboard_tab()
        self.setup_enroll_tab()
        self.setup_security_tab()
        self.setup_preferences_tab()

        self.tabs.currentChanged.connect(self.on_tab_changed)

    # -------------------------------------------------------------
    # TAB 1: DASHBOARD / OVERVIEW
    # -------------------------------------------------------------
    def setup_dashboard_tab(self):
        layout = QVBoxLayout(self.tab_dashboard)

        # Status Summary Box
        status_group = QGroupBox(tr("status_group"))
        status_layout = QVBoxLayout(status_group)

        self.lbl_camera_status = QLabel(tr("cam_status") + " ...")
        self.lbl_pam_status = QLabel(tr("pam_status") + " ...")
        self.lbl_gesture_status = QLabel(tr("gesture_status") + " ...")

        status_layout.addWidget(self.lbl_camera_status)
        status_layout.addWidget(self.lbl_pam_status)
        status_layout.addWidget(self.lbl_gesture_status)

        layout.addWidget(status_group)

        # Enrolled Profiles List
        users_group = QGroupBox(tr("users_group"))
        u_layout = QVBoxLayout(users_group)

        self.lbl_users_status = QLabel(tr("users_count") + " ...")
        u_layout.addWidget(self.lbl_users_status)

        self.list_users = QListWidget()
        u_layout.addWidget(self.list_users)

        btn_box = QHBoxLayout()
        self.btn_refresh_users = QPushButton(tr("btn_refresh"))
        self.btn_refresh_users.clicked.connect(self.refresh_user_list)

        btn_add_aspect = QPushButton(tr("btn_add_aspect"))
        btn_add_aspect.setObjectName("primaryBtn")
        btn_add_aspect.clicked.connect(lambda: self.tabs.setCurrentIndex(1))

        self.btn_delete_user = QPushButton(tr("btn_delete_user"))
        self.btn_delete_user.setObjectName("dangerBtn")
        self.btn_delete_user.clicked.connect(self.delete_selected_user)

        btn_box.addWidget(self.btn_refresh_users)
        btn_box.addWidget(btn_add_aspect)
        btn_box.addWidget(self.btn_delete_user)
        u_layout.addLayout(btn_box)

        layout.addWidget(users_group)

        # Quick Actions
        actions_group = QGroupBox(tr("actions_group"))
        a_layout = QHBoxLayout(actions_group)

        btn_test_live = QPushButton(tr("btn_test_live"))
        btn_test_live.clicked.connect(self.launch_live_test)
        a_layout.addWidget(btn_test_live)

        layout.addWidget(actions_group)
        layout.addStretch()

        self.refresh_dashboard_status()

    def refresh_dashboard_status(self):
        dev = config.get("camera", "device", "/dev/video0")
        if os.path.exists(dev):
            self.lbl_camera_status.setText(f"{tr('cam_status')} {dev} -> {tr('cam_connected')}")
            self.lbl_camera_status.setStyleSheet("color: #9ece6a;")
        else:
            self.lbl_camera_status.setText(f"{tr('cam_status')} {dev} -> {tr('cam_disconnected')}")
            self.lbl_camera_status.setStyleSheet("color: #f7768e;")

        if self.pam.is_module_installed():
            self.lbl_pam_status.setText(f"{tr('pam_status')} {tr('pam_installed')}")
            self.lbl_pam_status.setStyleSheet("color: #9ece6a;")
        else:
            self.lbl_pam_status.setText(f"{tr('pam_status')} {tr('pam_not_installed')}")
            self.lbl_pam_status.setStyleSheet("color: #e0af68;")

        thumbs = config.getboolean("security", "require_thumbs_up", False)
        if thumbs:
            self.lbl_gesture_status.setText(f"{tr('gesture_status')} {tr('gesture_active')}")
            self.lbl_gesture_status.setStyleSheet("color: #7dcfff;")
        else:
            self.lbl_gesture_status.setText(f"{tr('gesture_status')} {tr('gesture_inactive')}")
            self.lbl_gesture_status.setStyleSheet("color: #7aa2f7;")

        self.refresh_user_list()

    def refresh_user_list(self):
        self.list_users.clear()
        users = self.engine.list_enrolled_users()
        self.lbl_users_status.setText(f"{tr('users_count')} {len(users)}")
        for u in users:
            models_info = ", ".join([f"{m.get('name', 'Principal')} ({m.get('sample_count', '?')}m)" for m in u.get('models', [])])
            if not models_info:
                models_info = f"{u['sample_count']} muestras"
            item = QListWidgetItem(f"👤 {u['username']}  |  Aspectos: [{models_info}]  |  Fecha: {u['created_at'][:10]}")
            item.setData(Qt.ItemDataRole.UserRole, u['username'])
            self.list_users.addItem(item)

    def delete_selected_user(self):
        item = self.list_users.currentItem()
        if not item:
            QMessageBox.information(self, "VisageSoul", "Selecciona un usuario de la lista.")
            return

        username = item.data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro de que deseas eliminar el perfil facial de '{username}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            ok, msg = self.execute_elevated(
                ["remove", username],
                "Eliminar Perfil Facial",
                f"Introduce la contraseña de administrador para eliminar el perfil de '{username}':"
            )
            if ok:
                self.refresh_user_list()
                QMessageBox.information(self, "Éxito", f"Perfil de {username} eliminado.")
            else:
                QMessageBox.warning(self, "Error", f"No se pudo eliminar el perfil:\n{msg}")

    def launch_live_test(self):
        cli_bin = "/usr/local/bin/visagesoul"
        if not os.path.exists(cli_bin):
            cli_bin = str(Path(__file__).resolve().parent / "cli.py")
            cmd = [sys.executable, cli_bin, "test"]
        else:
            cmd = [cli_bin, "test"]
        subprocess.Popen(cmd)

    # -------------------------------------------------------------
    # TAB 2: ENROLLMENT
    # -------------------------------------------------------------
    def setup_enroll_tab(self):
        layout = QVBoxLayout(self.tab_enroll)

        # Video Preview
        self.video_label = QLabel(tr("enroll_title"))
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setFixedHeight(360)
        self.video_label.setStyleSheet("background: #0f1017; border: 2px solid #2f354a; border-radius: 8px;")
        layout.addWidget(self.video_label)

        # Progress bar
        self.progress_enroll = QProgressBar()
        self.progress_enroll.setRange(0, self.target_samples)
        self.progress_enroll.setValue(0)
        layout.addWidget(self.progress_enroll)

        self.lbl_status_msg = QLabel(tr("enroll_idle_msg"))
        self.lbl_status_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status_msg.setStyleSheet("font-weight: bold; color: #7dcfff;")
        layout.addWidget(self.lbl_status_msg)

        # Aspect selector (e.g. Con gafas, Sin gafas)
        aspect_layout = QHBoxLayout()
        lbl_aspect = QLabel(tr("enroll_aspect_label"))
        lbl_aspect.setStyleSheet("font-weight: bold; color: #bb9af7;")
        self.combo_aspect = QComboBox()
        self.combo_aspect.setEditable(True)
        self.combo_aspect.addItem("Principal (Sin gafas)")
        self.combo_aspect.addItem("Con Gafas (Glasses)")
        self.combo_aspect.addItem("Con Barba / Peinado")
        self.combo_aspect.addItem("Iluminación Diferente")
        aspect_layout.addWidget(lbl_aspect)
        aspect_layout.addWidget(self.combo_aspect)
        layout.addLayout(aspect_layout)

        # Controls
        ctrl_layout = QHBoxLayout()
        self.btn_start_enroll = QPushButton(tr("enroll_btn_start"))
        self.btn_start_enroll.setObjectName("primaryBtn")
        self.btn_start_enroll.setFixedHeight(42)
        self.btn_start_enroll.clicked.connect(self.toggle_enrollment)
        ctrl_layout.addWidget(self.btn_start_enroll)

        layout.addLayout(ctrl_layout)

    def toggle_enrollment(self):
        if not self.enrolling:
            self.enrolling = True
            self.enrolled_samples = []
            self.progress_enroll.setValue(0)
            self.btn_start_enroll.setText(tr("enroll_btn_stop"))
            self.lbl_status_msg.setText(tr("enroll_active_msg"))
        else:
            self.enrolling = False
            self.btn_start_enroll.setText(tr("enroll_btn_start"))
            self.lbl_status_msg.setText("Registro cancelado.")

    def process_camera_frame(self, frame: np.ndarray):
        display_frame = cv2.flip(frame, 1)
        raw_frame = frame
        h, w, _ = display_frame.shape

        faces = self.engine.detect_faces(raw_frame)
        primary_face = self.engine.get_primary_face(faces)

        if primary_face is not None:
            bx, by, bw, bh = int(primary_face[0]), int(primary_face[1]), int(primary_face[2]), int(primary_face[3])
            mirrored_bx = w - (bx + bw)
            cv2.rectangle(display_frame, (mirrored_bx, by), (mirrored_bx + bw, by + bh), (0, 255, 0), 2)

            if self.enrolling:
                now = time.time()
                if now - self.last_capture_time >= 0.35:
                    emb = self.engine.extract_embedding(raw_frame, primary_face)
                    self.enrolled_samples.append(emb)
                    self.last_capture_time = now
                    self.progress_enroll.setValue(len(self.enrolled_samples))
                    self.lbl_status_msg.setText(f"{tr('enroll_capturing', current=len(self.enrolled_samples), target=self.target_samples)}")

                    if len(self.enrolled_samples) >= self.target_samples:
                        self.enrolling = False
                        self.btn_start_enroll.setText(tr("enroll_btn_start"))
                        username = os.environ.get("SUDO_USER") or getpass.getuser()
                        label = self.combo_aspect.currentText().strip() or "Principal"

                        # Direct save first
                        saved_direct = self.engine.save_profile(
                            username,
                            self.enrolled_samples,
                            label=label,
                            append=True,
                            metadata={"camera": config.get("camera", "device", "/dev/video0")}
                        )

                        if saved_direct:
                            self.lbl_status_msg.setText(tr("enroll_success", label=label, user=username))
                            self.refresh_user_list()
                            play_chime("match")
                            QMessageBox.information(self, "Éxito", tr("enroll_success", label=label, user=username))
                        else:
                            temp_file = Path(f"/tmp/visagesoul_enroll_{username}_{int(time.time())}.json")
                            data = {
                                "username": username,
                                "label": label,
                                "created_at": datetime.datetime.now().isoformat(),
                                "sample_count": len(self.enrolled_samples),
                                "embeddings": [emb.tolist() for emb in self.enrolled_samples],
                                "metadata": {"camera": config.get("camera", "device", "/dev/video0")},
                            }
                            try:
                                with open(temp_file, "w", encoding="utf-8") as f:
                                    json.dump(data, f, indent=2)

                                ok, msg = self.execute_elevated(
                                    ["save-profile", "--user", username, "--file", str(temp_file)],
                                    "Guardar Perfil Facial",
                                    f"Introduce la contraseña de administrador para registrar el aspecto '{label}' de '{username}':"
                                )
                                if ok:
                                    self.lbl_status_msg.setText(tr("enroll_success", label=label, user=username))
                                    self.refresh_user_list()
                                    play_chime("match")
                                    QMessageBox.information(self, "Éxito", tr("enroll_success", label=label, user=username))
                                else:
                                    self.lbl_status_msg.setText("Error al guardar el perfil.")
                                    QMessageBox.warning(self, "Error", f"No se pudo guardar el perfil facial:\n{msg}")
                            finally:
                                if temp_file.is_file():
                                    try:
                                        temp_file.unlink()
                                    except Exception:
                                        pass

        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        qimg = QImage(rgb_frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(540, 360, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.video_label.setPixmap(pixmap)

    # -------------------------------------------------------------
    # TAB 3: SECURITY & PAM INTEGRATION
    # -------------------------------------------------------------
    def setup_security_tab(self):
        layout = QVBoxLayout(self.tab_security)

        # PAM Services
        pam_group = QGroupBox(tr("pam_services_group"))
        p_layout = QVBoxLayout(pam_group)

        self.chk_sddm = QCheckBox(tr("chk_sddm"))
        self.chk_kde = QCheckBox(tr("chk_kde"))
        self.chk_sudo = QCheckBox(tr("chk_sudo"))
        self.chk_polkit = QCheckBox(tr("chk_polkit"))

        self.load_pam_checkbox_states()

        p_layout.addWidget(self.chk_sddm)
        p_layout.addWidget(self.chk_kde)
        p_layout.addWidget(self.chk_sudo)
        p_layout.addWidget(self.chk_polkit)
        layout.addWidget(pam_group)

        # Unlock Rules & Gestures
        sec_group = QGroupBox(tr("security_rules_group"))
        s_form = QFormLayout(sec_group)

        self.chk_thumbs_up = QCheckBox(tr("chk_thumbs_up"))
        self.chk_thumbs_up.setChecked(config.getboolean("security", "require_thumbs_up", False))
        s_form.addRow("Doble Factor Gestual:", self.chk_thumbs_up)

        self.chk_auto_unlock = QCheckBox(tr("chk_auto_unlock"))
        self.chk_auto_unlock.setChecked(config.getboolean("security", "auto_unlock", True))
        s_form.addRow("Modo de Desbloqueo:", self.chk_auto_unlock)

        self.spin_max_attempts = QSpinBox()
        self.spin_max_attempts.setRange(1, 10)
        self.spin_max_attempts.setValue(config.getint("security", "max_attempts", 3))
        s_form.addRow(tr("max_attempts_label"), self.spin_max_attempts)

        layout.addWidget(sec_group)

        # Lock screen message
        msg_group = QGroupBox(tr("lock_msg_group"))
        m_form = QFormLayout(msg_group)

        self.chk_pam_notify = QCheckBox(tr("chk_pam_notify"))
        self.chk_pam_notify.setChecked(config.getboolean("pam", "notify", True))
        m_form.addRow("Mensaje Activo:", self.chk_pam_notify)

        self.edit_pam_msg = QLineEdit()
        self.edit_pam_msg.setText(config.get("pam", "message", "Iniciando sesión con VisageSoul..."))
        m_form.addRow(tr("pam_message_label"), self.edit_pam_msg)

        layout.addWidget(msg_group)

        # Save Button
        btn_apply_security = QPushButton(tr("btn_save_security"))
        btn_apply_security.setObjectName("primaryBtn")
        btn_apply_security.setFixedHeight(42)
        btn_apply_security.clicked.connect(self.save_security_settings)
        layout.addWidget(btn_apply_security)

        layout.addStretch()

    def load_pam_checkbox_states(self):
        statuses = self.pam.get_all_statuses()
        self.chk_sddm.setChecked(statuses.get("sddm", {}).get("enabled", False))
        self.chk_kde.setChecked(statuses.get("kde", {}).get("enabled", False))
        self.chk_sudo.setChecked(statuses.get("sudo", {}).get("enabled", False))
        self.chk_polkit.setChecked(statuses.get("polkit-1", {}).get("enabled", False))

    def save_security_settings(self):
        # 1. Update config values
        config.set("security", "require_thumbs_up", "true" if self.chk_thumbs_up.isChecked() else "false")
        config.set("security", "auto_unlock", "true" if self.chk_auto_unlock.isChecked() else "false")
        config.set("security", "max_attempts", self.spin_max_attempts.value())
        config.set("pam", "notify", "true" if self.chk_pam_notify.isChecked() else "false")
        config.set("pam", "message", self.edit_pam_msg.text().strip() or "Iniciando sesión con VisageSoul...")
        config.save()

        # 2. Apply PAM service changes
        sddm_val = "on" if self.chk_sddm.isChecked() else "off"
        kde_val = "on" if self.chk_kde.isChecked() else "off"
        sudo_val = "on" if self.chk_sudo.isChecked() else "off"
        polkit_val = "on" if self.chk_polkit.isChecked() else "off"

        apply_args = ["apply-pam", f"--sddm={sddm_val}", f"--kde={kde_val}", f"--sudo={sudo_val}", f"--polkit={polkit_val}"]

        ok, msg = self.execute_elevated(
            apply_args,
            "Autenticación de Administrador (PAM)",
            "Introduce tu contraseña de administrador para aplicar las reglas de seguridad en PAM:"
        )

        self.load_pam_checkbox_states()
        self.refresh_dashboard_status()

        if ok:
            QMessageBox.information(self, "Seguridad Aplicada", tr("security_saved"))
        else:
            QMessageBox.warning(self, "Aviso", f"Ajustes de seguridad guardados localmente, pero hubo un error al escribir reglas PAM:\n{msg}")

    # -------------------------------------------------------------
    # TAB 4: PREFERENCES & SYSTEM MAINTENANCE
    # -------------------------------------------------------------
    def setup_preferences_tab(self):
        layout = QVBoxLayout(self.tab_preferences)

        # Camera & Vision Settings
        cam_group = QGroupBox(tr("cam_settings_group"))
        c_form = QFormLayout(cam_group)

        self.combo_device = QComboBox()
        devices = list_video_devices()
        current_dev = config.get("camera", "device", "/dev/video0")
        for d in devices:
            self.combo_device.addItem(f"{d['path']} ({d['name']})", d["path"])
        c_form.addRow(tr("cam_device_label"), self.combo_device)

        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(0.50, 0.95)
        self.spin_threshold.setSingleStep(0.05)
        self.spin_threshold.setValue(config.getfloat("security", "threshold", 0.70))
        c_form.addRow(tr("threshold_label"), self.spin_threshold)

        self.spin_timeout = QDoubleSpinBox()
        self.spin_timeout.setRange(1.0, 15.0)
        self.spin_timeout.setSingleStep(0.5)
        self.spin_timeout.setValue(config.getfloat("security", "timeout", 4.0))
        c_form.addRow(tr("timeout_label"), self.spin_timeout)

        self.chk_low_light = QCheckBox(tr("chk_low_light"))
        self.chk_low_light.setChecked(config.getboolean("camera", "low_light_boost", True))
        c_form.addRow("Mejora de Imagen:", self.chk_low_light)

        layout.addWidget(cam_group)

        # Audio & Language
        audio_group = QGroupBox(tr("audio_lang_group"))
        a_form = QFormLayout(audio_group)

        self.chk_sound = QCheckBox(tr("chk_sound"))
        self.chk_sound.setChecked(config.getboolean("security", "sound_feedback", True))
        a_form.addRow("Efectos Sonoros:", self.chk_sound)

        sound_vol_layout = QHBoxLayout()
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(5, 100)
        self.slider_volume.setValue(config.getint("security", "sound_volume", 30))
        self.lbl_volume = QLabel(f"{self.slider_volume.value()}%")
        self.slider_volume.valueChanged.connect(lambda v: self.lbl_volume.setText(f"{v}%"))

        btn_test_sound = QPushButton(tr("btn_test_sound"))
        btn_test_sound.setMaximumWidth(90)
        btn_test_sound.clicked.connect(lambda: play_chime("success", volume_pct=self.slider_volume.value()))

        sound_vol_layout.addWidget(self.slider_volume)
        sound_vol_layout.addWidget(self.lbl_volume)
        sound_vol_layout.addWidget(btn_test_sound)
        a_form.addRow(tr("sound_vol_label"), sound_vol_layout)

        # Language Selector
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("🇪🇸 Español (es)", "es")
        self.combo_lang.addItem("🇺🇸 English (en)", "en")
        self.combo_lang.addItem("🌐 Automático / System Locale", "auto")
        cur_lang = config.get("general", "language", "auto").lower()
        idx = self.combo_lang.findData(cur_lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        a_form.addRow(tr("language_label"), self.combo_lang)

        layout.addWidget(audio_group)

        # System Maintenance & Diagnostics
        maint_group = QGroupBox(tr("system_tools_group"))
        m_layout = QHBoxLayout(maint_group)

        btn_doctor = QPushButton(tr("btn_doctor"))
        btn_doctor.clicked.connect(self.run_doctor_dialog)
        m_layout.addWidget(btn_doctor)

        btn_uninstall = QPushButton(tr("btn_uninstall"))
        btn_uninstall.setObjectName("dangerBtn")
        btn_uninstall.clicked.connect(self.run_uninstall_dialog)
        m_layout.addWidget(btn_uninstall)

        layout.addWidget(maint_group)

        # Save Button
        btn_save_pref = QPushButton(tr("btn_save_preferences"))
        btn_save_pref.setObjectName("primaryBtn")
        btn_save_pref.setFixedHeight(42)
        btn_save_pref.clicked.connect(self.save_preferences)
        layout.addWidget(btn_save_pref)

        layout.addStretch()

    def save_preferences(self):
        dev = self.combo_device.currentData()
        if dev:
            config.set("camera", "device", dev)
        config.set("security", "threshold", self.spin_threshold.value())
        config.set("security", "timeout", self.spin_timeout.value())
        config.set("security", "sound_feedback", "true" if self.chk_sound.isChecked() else "false")
        config.set("security", "sound_volume", self.slider_volume.value())
        config.set("camera", "low_light_boost", "true" if self.chk_low_light.isChecked() else "false")
        config.set("general", "language", self.combo_lang.currentData() or "auto")
        config.save()
        self.refresh_dashboard_status()
        QMessageBox.information(self, "Preferencias Guardadas", tr("preferences_saved"))

    def run_doctor_dialog(self):
        cli_bin = str(Path(__file__).resolve().parent / "cli.py")
        res = subprocess.run([sys.executable, cli_bin, "doctor"], capture_output=True, text=True)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("VisageSoul Doctor")
        msg_box.setText(res.stdout or "Diagnóstico completado sin salida.")
        msg_box.exec()

    def run_uninstall_dialog(self):
        confirm = QMessageBox.question(
            self,
            tr("uninst_confirm_title"),
            tr("uninst_confirm_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.execute_elevated(
            ["uninstall", "--yes"],
            "Desinstalación de VisageSoul",
            "Introduce tu contraseña de administrador para desinstalar VisageSoul:"
        )
        if ok:
            QMessageBox.information(self, "Desinstalación Exitosa", tr("uninst_success"))
            sys.exit(0)
        else:
            QMessageBox.warning(self, "Error en Desinstalación", f"No se pudo completar la desinstalación:\n{msg}")

    # -------------------------------------------------------------
    # TAB CHANGED & CAMERA LIFECYCLE
    # -------------------------------------------------------------
    def on_tab_changed(self, index: int):
        if index == 1:
            self.start_camera_worker()
        else:
            self.stop_camera_worker()

        if index == 0:
            self.refresh_dashboard_status()

    def start_camera_worker(self):
        if self.camera_worker is None or not self.camera_worker.isRunning():
            dev = config.get("camera", "device", "/dev/video0")
            self.camera_worker = CameraWorker(dev)
            self.camera_worker.frame_ready.connect(self.process_camera_frame)
            self.camera_worker.start()

    def stop_camera_worker(self):
        if self.camera_worker and self.camera_worker.isRunning():
            self.camera_worker.stop()
            self.camera_worker = None

    def closeEvent(self, event):
        self.stop_camera_worker()
        event.accept()


def launch_gui():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setApplicationName("VisageSoul")
    app.setDesktopFileName("visagesoul.desktop")
    app.setWindowIcon(get_app_icon())

    window = MainWindow()
    window.show()
    return app.exec()


def main():
    return launch_gui()


if __name__ == "__main__":
    sys.exit(main())
