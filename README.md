<p align="center">
  <img src="assets/visagesoul.svg" width="120" height="120" alt="VisageSoul logo">
</p>

<h1 align="center">VisageSoul</h1>

<p align="center">
  Facial and gesture-based biometric authentication for Linux systems.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-GPLv3-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/platform-Linux-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/C-PAM%20Module-00599C.svg" alt="C PAM">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow.svg" alt="Python">
</p>

---

VisageSoul is a lightweight, local biometric authentication system that integrates directly with Linux PAM (Pluggable Authentication Modules). It allows you to unlock your desktop session, log in via display managers, or run `sudo` using your webcam.

It uses OpenCV's YuNet for real-time face detection and SFace for 128-dimensional embedding extraction, combined with MediaPipe for optional hand gesture confirmation.

## Features

- **Session Auto-Unlock**: Seamlessly dismisses the lock screen via `systemd-logind` upon successful face match without requiring extra clicks.
- **Optional Gesture 2FA**: Require a physical thumbs-up gesture alongside face recognition to prevent accidental unlocks. Uses a hybrid geometric landmark classifier for angle and distance tolerance.
- **Multiple Aspects per Profile**: Register multiple facial conditions per user (e.g., with glasses, without glasses, different lighting conditions).
- **PAM Integration**: Native support for KDE Screen Locker (`kscreenlocker`), SDDM, GDM, LightDM, `sudo`, and Polkit.
- **Anti-Spoofing & Liveness**: 3D micro-movement variance analysis across consecutive frames to prevent flat photo spoofing.
- **Fail-Safe Fallback**: If the camera is busy, disconnected, or recognition times out, PAM immediately falls back to standard password authentication without locking you out.
- **Lockout Protection**: Configurable limit for failed attempts (default: 3) before temporarily forcing manual password entry.
- **Low-Light Compensation**: Automatic CLAHE (Contrast Limited Adaptive Histogram Equalization) for dark environments.
- **Qt6 Control Panel & CLI**: Graphical management dashboard alongside a complete command-line interface.
- **Bilingual Interface**: Built-in support for English and Spanish with automatic system locale detection.

## Prerequisites

- Linux system with `systemd` and PAM.
- Working webcam (V4L2 compatible).
- Dependencies: `gcc`, `make`, `pam` headers (`pam-devel` or `libpam0g-dev`), `python3` (3.10+), and `python-virtualenv`.

## Installation

Clone the repository and run the installer:

```bash
git clone https://github.com/Aetzax/visagesoul.git
cd visagesoul
sudo ./VisageSinstall.sh
```

The installer will:
1. Compile the native C PAM module (`pam_visagesoul.so`) into your system security libraries.
2. Download the required ONNX and MediaPipe neural models.
3. Set up the Python virtual environment and system binaries in `/opt/visagesoul/`.
4. Install desktop launchers and icons.

## Quick Start

### 1. Register your face

Run the interactive enrollment wizard:

```bash
# Register base profile
visagesoul enroll

# Register an additional aspect (e.g. wearing glasses)
visagesoul enroll --label "Glasses"
```

You can also use the graphical configurator:

```bash
visagesoul gui
```

### 2. Enable PAM Authentication

Enable VisageSoul for your desired services:

```bash
# Enable for KDE lock screen and SDDM
sudo visagesoul enable kde
sudo visagesoul enable sddm

# Enable for terminal sudo
sudo visagesoul enable sudo

# Enable for GUI authorization prompts
sudo visagesoul enable polkit-1
```

### 3. Test Recognition

Test your camera feed, face matching score, and gesture tracking in real time:

```bash
visagesoul test
```

## CLI Reference

| Command | Description |
| :--- | :--- |
| `visagesoul enroll [user] [--label "..."]` | Enroll a new face profile or aspect. |
| `visagesoul test [user]` | Run real-time camera and gesture diagnostics. |
| `visagesoul status` | Display system status, camera, and active PAM rules. |
| `visagesoul list` | List all enrolled users and their registered aspects. |
| `visagesoul remove <user>` | Delete a user's face profile. |
| `visagesoul enable <service>` | Enable PAM authentication for a service (`sddm`, `kde`, `sudo`, `polkit-1`, or `all`). |
| `visagesoul disable <service>` | Disable PAM authentication for a service. |
| `visagesoul doctor` | Run hardware, library, and permissions diagnostics. |
| `visagesoul gui` | Open the Qt6 graphical control panel. |

## Configuration

Settings are stored in `/etc/visagesoul/config.ini` (system-wide) with per-user overrides supported in `~/.config/visagesoul/config.ini`.

```ini
[camera]
device = /dev/video0
width = 1280
height = 720
fourcc = MJPG
fps = 30
warmup_frames = 5
low_light_boost = true

[security]
threshold = 0.70
timeout = 4.0
require_thumbs_up = false
auto_unlock = true
sound_feedback = true
sound_volume = 30
max_attempts = 3
attempts_window = 300

[pam]
notify = true
message = Authenticating with VisageSoul...
```

## Architecture & Security

- **Process Isolation**: The PAM module (`src/pam_visagesoul.c`) forks verification into a separate process with strict return code handling (`PAM_SUCCESS`, `PAM_AUTH_ERR`, `PAM_IGNORE`).
- **Input Sanitization**: Usernames are validated against path traversal patterns before filesystem operations.
- **Biometric Templates**: Facial embeddings are stored as 128-float cosine vectors. Raw images are discarded immediately after feature extraction.
- **Runtime State**: Attempt counters and rate-limiting data are stored in isolated runtime directories to prevent symlink attacks.

## Uninstallation

To cleanly remove VisageSoul and restore default PAM configurations:

```bash
sudo ./VisageSuninstall.sh
```

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
