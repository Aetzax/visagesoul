# Security Policy

## Biometric Scope and Known Limitations

VisageSoul is a multi-factor Face Anti-Spoofing (FAS) PAM module designed for generic RGB consumer webcams. Before reporting a vulnerability, please review our known hardware and biological limitations. **The following scenarios are considered known limitations and not valid security vulnerabilities:**

1. **Close Relatives & Identical Twins:** Standard 2D facial embeddings cannot differentiate between identical twins or close biological relatives with near-identical bone structure.
2. **Medical-Grade 3D Replicas:** Highly detailed, customized 3D silicone masks with accurate facial convexity and eye openings may bypass the 3D projective invariance (`std_geom`) and Neural Texture checks, as an RGB camera lacks dedicated IR structured-light depth sensors.
3. **Environmental Failures:** Pitch-black environments where the camera cannot resolve facial features, causing a denial of service (DoS) and forcing a password fallback.
4. **Local Root Compromise:** If an attacker already has `root` access to the machine, they can modify the `/etc/pam.d/` configurations or tamper with the neural models directly. This module assumes a trusted OS environment prior to the lock screen being invoked.

## Valid Vulnerabilities

We consider the following to be critical security vulnerabilities that should be reported immediately:
- Bypassing the authentication using a 2D printed photograph (despite the Blink Challenge and 3D parallax checks).
- Bypassing the authentication using a digital screen/tablet replay attack.
- Bugs in the PAM C-module (`pam_visagesoul.c`) that lead to crashes, memory leaks, authentication deadlocks, or unintended password bypasses.
- Privilege escalation vectors via the `visagesoul` command-line utility.

## Reporting a Vulnerability

Please **DO NOT** open a public issue for a security vulnerability. 

If you discover a vulnerability, we strongly encourage you to use GitHub's **Private Vulnerability Reporting** feature:
1. Go to the [Security tab](../../security) of this repository.
2. Click on **Report a vulnerability**.
3. Provide a detailed description of the attack vector, hardware used (if it's a presentation attack), and steps to reproduce.

Alternatively, you can reach out directly to the maintainer via email: `[INSERT YOUR EMAIL HERE]`

All security reports will be acknowledged within 48 hours, and we will work with you to patch the bypass before public disclosure.
