"""
PAM (Pluggable Authentication Modules) Configuration Manager for VisageSoul.
Handles safe insertion, verification, and rollback of PAM rules.
Compatible with /etc/pam.d and /usr/lib/pam.d architecture in Arch/CachyOS.
"""

import os
import shutil
import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

ETC_PAM_DIR = Path("/etc/pam.d")
USR_PAM_DIR = Path("/usr/lib/pam.d")
PAM_MODULE_NAME = "pam_visagesoul.so"
LEGACY_MODULE_NAME = "pam_aura_auth.so"
PAM_RULE_LINE = f"auth        sufficient    {PAM_MODULE_NAME}\n"

SUPPORTED_SERVICES = [
    "sddm", "kde", "sudo", "polkit-1",
    "gdm-password", "lightdm", "swaylock", "hyprlock",
    "system-auth", "system-login", "login"
]


class PamManager:
    def __init__(self, etc_pam_dir: Path = ETC_PAM_DIR, usr_pam_dir: Path = USR_PAM_DIR):
        self.etc_pam_dir = etc_pam_dir
        self.usr_pam_dir = usr_pam_dir

    def is_module_installed(self) -> bool:
        """Checks if the compiled pam_visagesoul.so exists in system security libraries."""
        possible_paths = [
            Path("/usr/lib/security") / PAM_MODULE_NAME,
            Path("/lib/security") / PAM_MODULE_NAME,
            Path("/usr/lib64/security") / PAM_MODULE_NAME,
            # Legacy fallback
            Path("/usr/lib/security") / LEGACY_MODULE_NAME,
        ]
        return any(p.is_file() for p in possible_paths)

    def get_service_path(self, service: str) -> Path:
        """Returns the active or target PAM file in /etc/pam.d."""
        return self.etc_pam_dir / service

    def get_system_default_path(self, service: str) -> Optional[Path]:
        """Returns fallback default in /usr/lib/pam.d if present."""
        path = self.usr_pam_dir / service
        return path if path.is_file() else None

    def get_service_status(self, service: str) -> Dict[str, Any]:
        """Checks if VisageSoul is enabled in a specific PAM service."""
        etc_path = self.get_service_path(service)
        usr_path = self.get_system_default_path(service)

        exists = etc_path.is_file() or (usr_path is not None)
        active_path = etc_path if etc_path.is_file() else usr_path

        if not exists:
            return {"exists": False, "enabled": False, "path": str(etc_path)}

        try:
            with open(active_path, "r", encoding="utf-8") as f:
                content = f.read()
            has_rule = (PAM_MODULE_NAME in content or LEGACY_MODULE_NAME in content)
            enabled = has_rule and not any(
                line.strip().startswith("#") and (PAM_MODULE_NAME in line or LEGACY_MODULE_NAME in line)
                for line in content.splitlines()
            )
            return {"exists": True, "enabled": enabled, "path": str(active_path)}
        except Exception as e:
            return {"exists": True, "enabled": False, "error": str(e), "path": str(active_path)}

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Returns status of all supported PAM services."""
        return {name: self.get_service_status(name) for name in SUPPORTED_SERVICES}

    def backup_service_file(self, service_path: Path) -> Optional[Path]:
        """Creates a timestamped backup before modifying a PAM file."""
        if not service_path.is_file():
            return None
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = service_path.parent / f"{service_path.name}.visagesoul.bak.{timestamp}"
        try:
            shutil.copy2(service_path, backup_path)
            return backup_path
        except PermissionError:
            print(f"Permiso denegado al crear copia de seguridad de {service_path}.")
            return None
        except Exception as e:
            print(f"Error creando copia de seguridad para {service_path}: {e}")
            return None

    def enable_service(self, service: str) -> Tuple[bool, str]:
        """Safely injects the PAM rule into the specified service in /etc/pam.d/."""
        if os.geteuid() != 0:
            return False, f"Se requieren permisos de administrador (root/sudo) para modificar /etc/pam.d/{service}."

        etc_path = self.get_service_path(service)
        usr_path = self.get_system_default_path(service)

        if not self.is_module_installed():
            return False, f"El módulo PAM {PAM_MODULE_NAME} no está instalado aún en /usr/lib/security/."

        # If file doesn't exist in /etc/pam.d, copy from /usr/lib/pam.d
        if not etc_path.is_file():
            if usr_path and usr_path.is_file():
                try:
                    self.etc_pam_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(usr_path, etc_path)
                except PermissionError:
                    return False, f"Permiso denegado: No se pudo copiar {usr_path} a {etc_path}."
                except Exception as e:
                    return False, f"Error al copiar {usr_path} a {etc_path}: {e}"
            else:
                return False, f"El archivo PAM para {service} no existe en /etc/pam.d ni /usr/lib/pam.d."

        # Read existing file
        try:
            with open(etc_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except PermissionError:
            return False, f"Permiso denegado al leer {etc_path}."
        except Exception as e:
            return False, f"Error al leer {etc_path}: {e}"

        # Clean legacy lines if present
        lines = [line for line in lines if LEGACY_MODULE_NAME not in line]

        # Check if already enabled with new module
        if any(PAM_MODULE_NAME in line and not line.strip().startswith("#") for line in lines):
            return True, f"VisageSoul ya está habilitado en {service}."

        # Create backup
        backup = self.backup_service_file(etc_path)
        if not backup:
            return False, f"No se pudo crear la copia de seguridad de {etc_path}. Operación abortada por seguridad."

        insert_idx = 0
        header_found = False
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#%PAM-1.0"):
                header_found = True
                insert_idx = idx + 1
                break

        if not header_found:
            for idx, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("auth") and not stripped.startswith("#"):
                    insert_idx = idx
                    break

        lines.insert(insert_idx, PAM_RULE_LINE)

        try:
            with open(etc_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True, f"VisageSoul habilitado exitosamente en {service}."
        except Exception as e:
            if backup and backup.is_file():
                shutil.copy2(backup, etc_path)
            return False, f"Error al escribir en {etc_path}: {e}"

    def disable_service(self, service: str) -> Tuple[bool, str]:
        """Removes the PAM rule from the specified service in /etc/pam.d/."""
        if os.geteuid() != 0:
            return False, f"Se requieren permisos de administrador (root/sudo) para modificar /etc/pam.d/{service}."

        etc_path = self.get_service_path(service)
        if not etc_path.is_file():
            return True, f"VisageSoul no está presente en /etc/pam.d/{service}."

        try:
            with open(etc_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except PermissionError:
            return False, f"Permiso denegado al leer {etc_path}."
        except Exception as e:
            return False, f"Error al leer {etc_path}: {e}"

        if not any((PAM_MODULE_NAME in line or LEGACY_MODULE_NAME in line) for line in lines):
            return True, f"VisageSoul no está activo en {service}."

        backup = self.backup_service_file(etc_path)
        new_lines = [line for line in lines if (PAM_MODULE_NAME not in line and LEGACY_MODULE_NAME not in line)]

        try:
            with open(etc_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            return True, f"VisageSoul desactivado correctamente en {service}."
        except Exception as e:
            if backup and backup.is_file():
                shutil.copy2(backup, etc_path)
            return False, f"Error al modificar {etc_path}: {e}"
