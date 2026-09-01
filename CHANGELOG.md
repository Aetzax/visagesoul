# Changelog

All notable changes to the **VisageSoul** project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.1] - 2026-09-01

### Fixed
- **Critical Gesture Engine Bug**: Fixed a `NameError` crash where `folded_count` was uninitialized, which caused the MediaPipe gesture fallback to silently fail and always return `None`.
- **False Positives in Anti-Spoofing**: Removed the permanent session taint lock from MiniFASNet to prevent a single bad frame (e.g. from lighting changes) from permanently locking out the user as a "Foto impresa".
- **Rigidity Check Tuning**: Significantly relaxed the 3D parallax `std_geom` and `mad_geom` thresholds (from 0.0120 to 0.0050) to allow users to authenticate while sitting naturally still, reducing false rejections.
- **Hand Rigidity Disabled**: Disabled the strict static gesture requirement (`std_dist`) for 2FA gestures which required users to wobble their hand.

## [1.2.0] - 2026-09-01

### Added
- **Multi-Layer Face Anti-Spoofing (FAS) Engine (`AntiSpoofEngine`)**:
  - **2D Fourier Moire Screen Detection**: Identifies smartphone, tablet, and monitor OLED/LCD subpixel grid harmonics in the frequency spectrum.
  - **Eye Micro-Gradient Dynamics**: Analyzes micro-sacádicos, iris contrast, and natural blink dynamics across consecutive frames to reject static paper photos.
  - **3D Non-Rigid Parallax Tracking**: Evaluates dynamic perspective changes between eyes, nose, and mouth landmarks.
  - **Real-Time Visual Anti-Spoofing Feedback**: Immediate warnings (`⚠️ Pantalla digital detectada`, `⚠️ Foto estática detectada`) in `visagesoul test`.
- **Selectable 2FA Confirmation Gestures**:
  - Added user selection between **👍 Thumbs Up (*Thumb Up*)**, **🖐️ Open Palm (*Open Palm*)**, and **🔄 Both (*Thumb Up or Open Palm*)**.
  - New dropdown in GUI Preferences & Security tab with automatic state persistence.
- **Enhanced CLI Interactive Help**:
  - Comprehensive `--help` banner with color coding, subcommands overview, and usage examples.
- **Bilingual Default PAM Message**:
  - Default status text changed to `"Esperando biometría..."` (ES) / `"Waiting for biometrics..."` (EN).
- **Official Links & Credits**:
  - Added GitHub repository button and PayPal donation link (`paypal.me/aetzax1`) in GUI and CLI.

### Fixed
- **Permission Denied on Profile Save (`/etc/visagesoul/faces`)**:
  - Enforced standard `0755` permissions on `/etc/visagesoul/faces` and `0644` on `.json` files, preventing Linux kernel `fs.protected_regular` permission errors.
  - Implemented atomic file replacement (`os.replace` via `.tmp` files).
- **Liveness Bypass when Gesture 2FA was enabled**:
  - Removed conditional check that was inadvertently skipping liveness verification when gesture mode was active.
- **Password Prompt during Facial Enrollment**:
  - Enforced mandatory password elevation before writing biometric profiles to disk.

---

## [1.1.0] - 2026-08-31

### Added
- **Bypass Welcome Page (Hands-Free Direct Boot)**:
  - Automatic SDDM / Display Manager autologin with immediate lock screen biometric scan on boot.
- **Aspects Manager in GUI**:
  - Support for enrolling multiple appearance models (*Sin gafas*, *Con gafas*, *De noche*) per user profile.
- **Audio Feedback / Chimes**:
  - Subtly tuned notification sounds for successful match and authorization.
- **KDE Plasma & Wayland Integration**:
  - Native Tokyo Night dark theme and SVG iconography for the Qt6 control panel.

### Security
- **Intelligent Recursion Bypass in C PAM Module**:
  - Direct `/proc/$PPID/cmdline` inspection in `pam_visagesoul.c` to prevent hardware lockouts during administrative commands.
- **Lockout Protection**:
  - Configurable max failed attempts threshold before enforcing manual password fallback.

---

## [1.0.0] - 2026-08-25

### Initial Release
- Native C PAM security module (`pam_visagesoul.so`).
- Real-time YuNet face detector + SFace 128D cosine embedding extractor.
- CLAHE adaptive histogram equalization for low-light environments.
- Support for KDE `kscreenlocker`, SDDM, GDM, LightDM, `sudo`, and Polkit.
