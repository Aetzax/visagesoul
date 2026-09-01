<p align="center">
  <img src="assets/visagesoul.svg" width="120" height="120" alt="VisageSoul logo">
</p>

<h1 align="center">VisageSoul</h1>

<p align="center">
  <strong>Fast, secure Windows Hello alternative for Linux with facial and gesture-based biometric authentication.</strong><br>
  <em>Unlock your desktop, authenticate sudo, and log in with your webcam in 0.3s.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-GPLv3-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/platform-Linux-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/C-PAM%20Module-00599C.svg" alt="C PAM">
</p>

---

**VisageSoul** integrates seamlessly with Linux PAM to provide ultra-fast biometric face unlock for your desktop lock screen (SDDM, GDM, KDE), Polkit windows, and terminal `sudo`. It is powered by state-of-the-art neural vision models (**YuNet**, **SFace**, **MiniFASNet V2**, and **MediaPipe**) to offer robust Multi-Layer Face Anti-Spoofing (FAS).

---

## Installation

Clone the repository and run the installer:

```bash
git clone https://github.com/Aetzax/visagesoul.git
cd visagesoul
sudo ./VisageSinstall.sh
```
This compiles the native C PAM module, sets up the models, and installs the desktop shortcuts.

---

## Quick Start

The easiest way to configure VisageSoul is through the **Graphical User Interface (GUI)**. 
Simply search for "VisageSoul" in your application menu or run:

```bash
visagesoul gui
```

From the control panel, you can:
1. **Enroll your face:** Add or remove users visually.
2. **Enable PAM integrations:** Toggle VisageSoul on/off for `sudo`, `kde`, `sddm`, or `polkit-1` with a single click.
3. **Configure Security:** Adjust strictness thresholds, timeout limits, and choose your 2FA Gesture (Thumbs Up, Open Palm, or None).

### Command Line Interface
If you prefer the terminal, you can manage the system via the command line:
- `visagesoul enroll` - Register a new face.
- `visagesoul enable <service>` - Enable PAM (e.g., `sudo visagesoul enable sudo`).
- `visagesoul disable <service>` - Remove PAM integration.
- `visagesoul test` - Test camera, recognition, and liveness in real-time.
- `visagesoul status` - View system configuration.

---

## Features & Security

VisageSoul uses a defense-in-depth architecture to prevent spoofing attacks such as printed photos, digital screens, and replays:

1. **Blink Challenge (Active Liveness):** Requires a physical eyelid closure (blink) using MediaPipe Face Landmarker, making static photo bypass impossible.
2. **Deep Neural Anti-Spoofing (MiniFASNet V2):** Distinguishes real skin textures from paper grain or OLED screen emission. Triggers a permanent session lockout if an attack is detected.
3. **3D Facial Geometry Parallax:** Analyzes the relative distance between eyes and nose across multiple frames to reject flat 2D surfaces.
4. **Fourier Transform Moiré Filter:** Scans the 2D frequency spectrum of the face to detect artificial sub-pixel grids (Moiré) and glass glare from phones.
5. **Gesture 2FA (Optional):** Requires physical, intentional hand gestures to confirm authentication, ensuring independent biomechanical movement.

> **Security Limitations & Policies:** Please refer to [`SECURITY.md`](SECURITY.md) for vulnerability reporting and biometric scope limits (e.g., identical twins, 3D masks).

---

## Uninstallation

To cleanly remove VisageSoul and restore default PAM configurations:

```bash
sudo ./VisageSuninstall.sh
```

---

## Academic References & Architecture

The biometric defense and validation architecture (Face Anti-Spoofing) of this project is strongly aligned with and inspired by the fusion methodologies (hybrid architectures) detailed in contemporary academic research.

In particular, the combination of textural neural networks, 3D parallax geometric analysis, and dynamic active liveness challenges (blinking) directly follows the security recommendations for limited hardware environments (standard RGB webcams) detailed in:

* **Ming, Z., Luqman, M. M., & Burie, J. C. (2020).** *"A Survey On Anti-Spoofing Methods For Face Recognition with RGB Cameras of Generic Consumer Devices"*. arXiv preprint [arXiv:2010.04145](https://arxiv.org/abs/2010.04145).

---

## Support & Donations

If you find VisageSoul useful and want to support ongoing development:
- **PayPal:** [paypal.me/aetzax1](https://paypal.me/aetzax1)

---

## License
Licensed under the [GNU General Public License v3.0](LICENSE).
