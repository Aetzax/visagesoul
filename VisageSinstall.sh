#!/usr/bin/env bash
# ==============================================================================
# ✨ VisageSoul: Instalador Automático para Linux (SDDM / KDE Plasma / sudo)
# ==============================================================================
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${PURPLE}"
echo " __     ___                            ____             _"
echo " \ \   / (_)___  __ _  __ _  ___      / ___|  ___  _   _| |"
echo "  \ \ / /| / __|/ _\` |/ _\` |/ _ \ ____\___ \ / _ \| | | | |"
echo "   \ V / | \__ \ (_| | (_| |  __/_____|___) | (_) | |_| | |"
echo "    \_/  |_|___/\__,_|\__, |\___|     |____/ \___/ \__,_|_|"
echo "                      |___/                                 "
echo -e "${NC}"
echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}   ✨ VisageSoul v1.0.0 (Build 2026.08.31) — Biometrics Linux   ${NC}"
echo -e "${CYAN}================================================================${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Solicitando permisos de administrador (sudo)...${NC}"
    exec sudo bash "$0" "$@"
fi

ACTUAL_USER="${SUDO_USER:-$USER}"

echo -e "\n${BLUE}1. Compilando módulo PAM e instalando componentes en /opt/visagesoul...${NC}"
make install

# Migrate legacy face data if exists
if [ -d "/etc/aura-auth/faces" ] && [ -n "$(ls -A /etc/aura-auth/faces 2>/dev/null)" ]; then
    echo -e "  -> Migrando perfiles biométricos anteriores..."
    cp -n /etc/aura-auth/faces/*.json /etc/visagesoul/faces/ 2>/dev/null || true
fi

ENABLE_DEBUG=false
for arg in "$@"; do
    if [ "$arg" == "--debug" ] || [ "$arg" == "-d" ]; then
        ENABLE_DEBUG=true
    fi
done

if [ "$ENABLE_DEBUG" = true ]; then
    echo -e "  -> Modo de depuración activado: Los logs se guardarán en /tmp/visagesoul_verify.log"
    sed -i 's/^debug\s*=.*/debug = true/' /etc/visagesoul/config.ini 2>/dev/null || true
else
    sed -i 's/^debug\s*=.*/debug = false/' /etc/visagesoul/config.ini 2>/dev/null || true
fi

# Ensure gesture 2FA is active by default as recommended
sed -i 's/^require_thumbs_up\s*=.*/require_thumbs_up = true/' /etc/visagesoul/config.ini 2>/dev/null || true
grep -q "require_gesture" /etc/visagesoul/config.ini 2>/dev/null || sed -i '/\[security\]/a require_gesture = true' /etc/visagesoul/config.ini 2>/dev/null || true
sed -i 's/^gesture_type\s*=.*/gesture_type = both/' /etc/visagesoul/config.ini 2>/dev/null || true
grep -q "gesture_type" /etc/visagesoul/config.ini 2>/dev/null || sed -i '/\[security\]/a gesture_type = both' /etc/visagesoul/config.ini 2>/dev/null || true

chmod 755 /etc/visagesoul
chmod 644 /etc/visagesoul/config.ini 2>/dev/null || true
chmod 755 /etc/visagesoul/faces
chmod 644 /etc/visagesoul/faces/*.json 2>/dev/null || true
chown -R root:root /etc/visagesoul 2>/dev/null || true

echo -e "\n${BLUE}2. Actualizando caché de iconos y lanzadores del sistema...${NC}"
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database /usr/share/applications 2>/dev/null || true
kbuildsycoca6 2>/dev/null || true

if [ -n "$ACTUAL_USER" ] && [ "$ACTUAL_USER" != "root" ]; then
    USER_HOME=$(eval echo "~$ACTUAL_USER")
    rm -f "$USER_HOME/.cache/plasma_theme_"*.kcache "$USER_HOME/.cache/ksycoca6"* 2>/dev/null || true
    su - "$ACTUAL_USER" -c "kbuildsycoca6 --noincremental 2>/dev/null || true" 2>/dev/null || true
fi

echo -e "\n${BLUE}3. Comprobando instalación con VisageSoul Doctor...${NC}"
/usr/local/bin/visagesoul doctor || true

echo -e "\n${GREEN}=======================================================${NC}"
echo -e "${GREEN}   🎉 ¡Instalación de VisageSoul completada con éxito!   ${NC}"
echo -e "${GREEN}=======================================================${NC}"
echo -e "Puedes abrir la interfaz gráfica en cualquier momento con: ${YELLOW}visagesoul gui${NC}"
echo -e "O registrar tu rostro en la terminal con:                 ${YELLOW}visagesoul enroll${NC}\n"
