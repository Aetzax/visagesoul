"""
VisageSoul Internationalization (i18n) Engine.
Supports English (en) and Spanish (es) with auto-detection.
"""

import os
import locale
from typing import Dict
from .config import config

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "es": {
        # App & Header
        "app_title": "VisageSoul — Biometría Facial & Gestual para Linux",
        "app_subtitle": "Autenticación Biométrica Facial & Gestual para Linux",
        "tab_dashboard": "📊 Estado General",
        "tab_enroll": "📷 Registro Facial",
        "tab_security": "🛡️ Seguridad y PAM",
        "tab_preferences": "⚙️ Preferencias y Sistema",

        # Dashboard
        "status_group": "Estado del Sistema",
        "cam_status": "📷 Cámara Principal:",
        "cam_connected": "[CONECTADA]",
        "cam_disconnected": "[NO DETECTADA]",
        "pam_status": "🛡️ Módulo PAM (pam_visagesoul.so):",
        "pam_installed": "[INSTALADO Y ACTIVO]",
        "pam_not_installed": "[NO INSTALADO]",
        "gesture_status": "👍 Confirmación Gestual:",
        "gesture_active": "[ACTIVADO - PULGAR ARRIBA]",
        "gesture_inactive": "[DESACTIVADO - SOLO ROSTRO]",
        "users_group": "Perfiles y Aspectos Faciales",
        "users_count": "👤 Usuarios Registrados con VisageSoul:",
        "samples_label": "muestras biométricas",
        "btn_refresh": "🔄 Actualizar",
        "btn_delete_user": "🗑️ Eliminar Perfil",
        "btn_add_aspect": "➕ Nuevo Aspecto",
        "actions_group": "Acciones Rápidas",
        "btn_quick_enroll": "📷 Nuevo Aspecto Facial",
        "btn_test_live": "👁️ Probar Reconocimiento en Vivo",

        # Enrollment
        "enroll_title": "Feed de Cámara en Vivo",
        "enroll_aspect_label": "🏷️ Aspecto / Condición:",
        "enroll_idle_msg": "Pulsa 'Iniciar Registro' y mira fijamente a la cámara.",
        "enroll_active_msg": "Mira fijamente a la cámara y gira suavemente la cabeza...",
        "enroll_btn_start": "🎬 Iniciar Registro",
        "enroll_btn_stop": "🛑 Detener Registro",
        "enroll_success": "¡Aspecto '{label}' registrado correctamente para {user}!",
        "enroll_capturing": "Capturando muestras: {current} / {target}",

        # Security & PAM Tab
        "pam_services_group": "Servicios de Autenticación PAM",
        "chk_sddm": "Habilitar en Inicio de Sesión (SDDM / GDM)",
        "chk_kde": "Habilitar en Pantalla de Bloqueo (KDE / kscreenlocker)",
        "chk_sudo": "Habilitar en Terminal (sudo)",
        "chk_polkit": "Habilitar en Ventanas de Permisos (Polkit)",
        "security_rules_group": "Reglas de Desbloqueo y Gestos",
        "chk_thumbs_up": "Exigir gesto de pulgar arriba (👍) para confirmar el desbloqueo",
        "chk_auto_unlock": "Desbloqueo instantáneo automático (sin pulsar botones)",
        "max_attempts_label": "Intentos fallidos antes de forzar contraseña (1-10):",
        "lock_msg_group": "Mensajes en Pantalla de Bloqueo",
        "chk_pam_notify": "Mostrar mensaje informativo en pantalla de bloqueo",
        "pam_message_label": "Texto del mensaje:",
        "btn_save_security": "💾 Guardar y Aplicar Ajustes de Seguridad",
        "security_saved": "Configuración de seguridad y reglas PAM aplicadas exitosamente.",

        # Preferences & System Tab
        "cam_settings_group": "Cámara y Visión Artificial",
        "cam_device_label": "Dispositivo de Cámara:",
        "threshold_label": "Umbral de Similitud (Recomendado 0.70):",
        "timeout_label": "Tiempo Máximo de Escaneo (Segundos):",
        "chk_low_light": "Compensación automática para habitaciones oscuras (CLAHE)",
        "audio_lang_group": "Audio e Idioma",
        "chk_sound": "Reproducir sonido agradable al desbloquear con éxito",
        "sound_vol_label": "Volumen del Sonido:",
        "btn_test_sound": "🎵 Probar",
        "language_label": "Idioma de la Interfaz / Language:",
        "system_tools_group": "Herramientas y Mantenimiento del Sistema",
        "btn_doctor": "🩺 Diagnóstico del Sistema (VisageSoul Doctor)",
        "btn_uninstall": "🗑️ Desinstalar VisageSoul del Sistema",
        "btn_save_preferences": "💾 Guardar Preferencias",
        "preferences_saved": "Preferencias de VisageSoul guardadas correctamente.",
        "uninst_confirm_title": "Confirmar Desinstalación",
        "uninst_confirm_msg": "¿Estás seguro de que deseas desinstalar VisageSoul de tu sistema?\n\nLas reglas PAM de SDDM y KDE volverán al estado predeterminado de contraseña.",
        "uninst_success": "VisageSoul ha sido desinstalado correctamente de tu sistema.\n\nLa aplicación se cerrará ahora.",
    },
    "en": {
        # App & Header
        "app_title": "VisageSoul — Biometric Face & Gesture Auth for Linux",
        "app_subtitle": "Next-Gen Biometric Facial & Gestural Authentication for Linux",
        "tab_dashboard": "📊 Overview",
        "tab_enroll": "📷 Face Profiles",
        "tab_security": "🛡️ Security & PAM",
        "tab_preferences": "⚙️ Preferences & System",

        # Dashboard
        "status_group": "System Status",
        "cam_status": "📷 Main Camera:",
        "cam_connected": "[CONNECTED]",
        "cam_disconnected": "[NOT DETECTED]",
        "pam_status": "🛡️ PAM Module (pam_visagesoul.so):",
        "pam_installed": "[INSTALLED & ACTIVE]",
        "pam_not_installed": "[NOT INSTALLED]",
        "gesture_status": "👍 Gesture Confirmation:",
        "gesture_active": "[ENABLED - THUMBS UP]",
        "gesture_inactive": "[DISABLED - FACE ONLY]",
        "users_group": "Face Profiles and Aspects",
        "users_count": "👤 Users Enrolled in VisageSoul:",
        "samples_label": "biometric samples",
        "btn_refresh": "🔄 Refresh",
        "btn_delete_user": "🗑️ Delete Profile",
        "btn_add_aspect": "➕ New Aspect",
        "actions_group": "Quick Actions",
        "btn_quick_enroll": "📷 New Face Aspect",
        "btn_test_live": "👁️ Test Live Recognition",

        # Enrollment
        "enroll_title": "Live Camera Feed",
        "enroll_aspect_label": "🏷️ Aspect / Condition:",
        "enroll_idle_msg": "Press 'Start Enrollment' and look directly into the camera.",
        "enroll_active_msg": "Look directly at the camera and gently turn your head...",
        "enroll_btn_start": "🎬 Start Enrollment",
        "enroll_btn_stop": "🛑 Stop Enrollment",
        "enroll_success": "Aspect '{label}' successfully enrolled for {user}!",
        "enroll_capturing": "Capturing samples: {current} / {target}",

        # Security & PAM Tab
        "pam_services_group": "PAM Authentication Services",
        "chk_sddm": "Enable on Login Screen (SDDM / GDM)",
        "chk_kde": "Enable on Lock Screen (KDE / kscreenlocker)",
        "chk_sudo": "Enable in Terminal (sudo)",
        "chk_polkit": "Enable in Authorization Dialogs (Polkit)",
        "security_rules_group": "Unlock Rules & Gestures",
        "chk_thumbs_up": "Require thumbs-up gesture (👍) to confirm authentication",
        "chk_auto_unlock": "Instant auto-unlock (no extra buttons or pause)",
        "max_attempts_label": "Max failed attempts before forcing password (1-10):",
        "lock_msg_group": "Lock Screen Message",
        "chk_pam_notify": "Show status message on lock screen",
        "pam_message_label": "Message text:",
        "btn_save_security": "💾 Save & Apply Security Rules",
        "security_saved": "Security configuration and PAM rules applied successfully.",

        # Preferences & System Tab
        "cam_settings_group": "Camera & Computer Vision",
        "cam_device_label": "Camera Device:",
        "threshold_label": "Similarity Threshold (Recommended 0.70):",
        "timeout_label": "Scan Timeout (Seconds):",
        "chk_low_light": "Automatic low-light compensation (CLAHE)",
        "audio_lang_group": "Audio & Language",
        "chk_sound": "Play pleasant audio chime upon successful unlock",
        "sound_vol_label": "Sound Volume:",
        "btn_test_sound": "🎵 Test",
        "language_label": "Interface Language / Idioma:",
        "system_tools_group": "System Tools & Maintenance",
        "btn_doctor": "🩺 System Diagnostics (VisageSoul Doctor)",
        "btn_uninstall": "🗑️ Uninstall VisageSoul from System",
        "btn_save_preferences": "💾 Save Preferences",
        "preferences_saved": "VisageSoul preferences saved successfully.",
        "uninst_confirm_title": "Confirm Uninstallation",
        "uninst_confirm_msg": "Are you sure you want to uninstall VisageSoul from your system?\n\nPAM authentication rules will be restored to default password state.",
        "uninst_success": "VisageSoul has been uninstalled successfully.\n\nThe application will now close.",
    }
}


def get_current_language() -> str:
    """Returns the effective language code ('es' or 'en')."""
    cfg_lang = config.get("general", "language", "auto").lower()
    if cfg_lang in ("es", "en"):
        return cfg_lang

    try:
        sys_lang = os.environ.get("LANG", "") or locale.getdefaultlocale()[0] or ""
        if sys_lang.lower().startswith("es"):
            return "es"
    except Exception:
        pass

    return "en"


def tr(key: str, **kwargs) -> str:
    """Translates a key into the active language with variable interpolation."""
    lang = get_current_language()
    text = TRANSLATIONS.get(lang, {}).get(key)
    if text is None:
        text = TRANSLATIONS.get("en", {}).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
