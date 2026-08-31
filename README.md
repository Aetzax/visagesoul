# ✨ VisageSoul: Next-Gen Biometric Facial & Gestural Authentication for Linux

<p align="center">
  <img src="assets/visagesoul.svg" width="140" height="140" alt="VisageSoul Logo">
</p>

<p align="center">
  <b>Biometría Facial y Gestual de Última Generación para Linux</b><br>
  <i>Integración fluida para SDDM, KDE Plasma (kscreenlocker), sudo y Polkit.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Language-Python%20%7C%20C-blue.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Desktop-KDE%20Plasma%20%7C%20Wayland-blueviolet.svg" alt="Desktop">
  <img src="https://img.shields.io/badge/Hardware-Logitech%20StreamCam%20%7C%20V4L2-success.svg" alt="Camera">
  <img src="https://img.shields.io/badge/License-GPL3-green.svg" alt="License">
</p>

---

## 🌟 Características Principales (Key Features)

- ⚡ **Desbloqueo Instantáneo Automático (Auto-Continue)**: Pasa directamente al escritorio en cuanto te reconoce, eliminando cualquier botón o pausa en la pantalla de bloqueo.
- 👍 **Doble Factor Gestual (Pulgar Arriba / Thumbs-Up)**: Permite requerir levantar el pulgar ante la cámara como confirmación explícita de desbloqueo, evitando accesos involuntarios.
- 🎵 **Efectos de Sonido (Audio Chimes)**: Retroalimentación sonora agradable al iniciar sesión con éxito (estilo macOS / Windows Hello).
- 🌙 **Compensación de Poca Luz (CLAHE)**: Algoritmo de visión artificial adaptativo para reconocer tu rostro en habitaciones oscuras o de noche.
- 🌐 **Soporte Bilingüe (i18n)**: Interfaz y mensajes disponibles en **Español 🇪🇸** e **Inglés 🇺🇸** con detección automática.
- 📷 **Optimizado para Logitech StreamCam**: Auto-exposición y warmup de fotogramas calibrados para hardware moderno.
- 🛡️ **Seguridad Total & Fallback Inmediato**: Si la cámara no te ve o no hay luz, el sistema pasa inmediatamente a pedir tu contraseña tradicional sin bloquearte.
- 🎨 **Configurador Gráfico Qt6**: Interfaz visual moderna integrada en KDE Plasma con modo oscuro y permisos Polkit / sudo.
- 🗑️ **Desinstalador Seguro en 1-Click**: Scripts oficiales `VisageSinstall.sh` y `VisageSuninstall.sh` para instalar y desinstalar de forma limpia y segura.

---

## 🚀 Instalación (Quick Start)

Ejecuta el instalador oficial desde la carpeta del proyecto:

```bash
cd "/home/aetzax/Proyectos/linux auth face"
sudo ./VisageSinstall.sh
```

---

## 🎮 Uso y Configuración

### 1. Interfaz Gráfica (GUI)
Abre el configurador visual en cualquier momento:
```bash
visagesoul gui
```
*(O búscalo como **VisageSoul** en el lanzador de aplicaciones de KDE Plasma).*

### 2. Comandos de Terminal (CLI)

```bash
# 1. Registrar tu rostro
visagesoul enroll

# 2. Probar la cámara, reconocimiento facial y gestos en tiempo real
visagesoul test

# 3. Comprobar el estado general del sistema y servicios PAM
visagesoul status

# 4. Activar o desactivar en SDDM y la pantalla de bloqueo de KDE
sudo visagesoul enable sddm
sudo visagesoul enable kde

# 5. Ejecutar diagnóstico de dependencias y cámara
visagesoul doctor

# 6. Desinstalar VisageSoul del sistema
sudo ./VisageSuninstall.sh
# (o sudo visagesoul uninstall)
```

---

## 🏗️ Arquitectura Técnica

- **Módulo PAM (`src/pam_visagesoul.c`)**: Módulo nativo compilado en C (`pam_visagesoul.so`) con aislamiento de procesos `fork()` y fallback a prueba de fallos.
- **Redes Neuronales de IA**:
  - **YuNet ONNX**: Detección facial ultrarrápida multiescala (~10ms).
  - **SFace ONNX**: Extracción de vectores faciales de 128 dimensiones y distancia coseno.
  - **MediaPipe Gesture Recognizer**: Detección de pose y gesto de pulgar arriba en tiempo real.
- **Auto-Unlock Daemon**: Integración directa con `systemd-logind` (`loginctl unlock-session`).

---

## 📄 Licencia

Este proyecto está bajo la licencia **GNU General Public License v3.0 (GPLv3)**.
