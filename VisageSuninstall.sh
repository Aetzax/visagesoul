#!/usr/bin/env bash
# ==============================================================================
# ✨ VisageSoul: Desinstalador Oficial para Linux
# ==============================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${RED}"
echo " __     ___                            ____             _"
echo " \ \   / (_)___  __ _  __ _  ___      / ___|  ___  _   _| |"
echo "  \ \ / /| / __|/ _\` |/ _\` |/ _ \ ____\___ \ / _ \| | | | |"
echo "   \ V / | \__ \ (_| | (_| |  __/_____|___) | (_) | |_| | |"
echo "    \_/  |_|___/\__,_|\__, |\___|     |____/ \___/ \__,_|_|"
echo "                      |___/                                 "
echo -e "${NC}"
echo -e "${RED}================================================================${NC}"
echo -e "${RED}   🗑️  VisageSuninstall v1.0.0 (2026.08.31) — VisageSoul Cleaner   ${NC}"
echo -e "${RED}================================================================${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Solicitando permisos de administrador (sudo)...${NC}"
    exec sudo bash "$0" "$@"
fi

PURGE=false
if [[ "$*" == *"--purge"* ]]; then
    PURGE=true
else
    echo -e "\n${YELLOW}¿Deseas eliminar también tus perfiles faciales registrados? (s/N):${NC} "
    read -r response
    if [[ "$response" =~ ^([sS][iI]|[sS]|[yY][eE][sS]|[yY])$ ]]; then
        PURGE=true
    fi
fi

echo -e "\n${BLUE}1. Desactivando reglas de inicio de sesión en PAM de forma segura...${NC}"
for pam_file in /etc/pam.d/*; do
    if [ -f "$pam_file" ]; then
        if grep -q "pam_visagesoul.so" "$pam_file" 2>/dev/null || grep -q "pam_aura_auth.so" "$pam_file" 2>/dev/null; then
            echo -e "  -> Limpiando reglas en ${CYAN}$pam_file${NC}..."
            sed -i '/pam_visagesoul.so/d' "$pam_file"
            sed -i '/pam_aura_auth.so/d' "$pam_file"
        fi
    fi
done

echo -e "\n${BLUE}2. Eliminando componentes de VisageSoul y limpiando gestores de inicio...${NC}"
# Limpiar Bypass Welcome Page y Autologin
rm -f /etc/sddm.conf.d/autologin.conf
rm -f /etc/lightdm/lightdm.conf.d/80-visagesoul-autologin.conf
for gdm_conf in /etc/gdm/custom.conf /etc/gdm3/custom.conf; do
    if [ -f "$gdm_conf" ]; then
        sed -i '/AutomaticLogin/d' "$gdm_conf"
    fi
done
rm -f /home/*/.config/autostart/visagesoul-startup-lock.desktop
rm -f /root/.config/autostart/visagesoul-startup-lock.desktop
rm -rf /run/visagesoul /tmp/visagesoul_*

rm -rf /opt/visagesoul
rm -rf /opt/aura-auth
rm -f /usr/lib/security/pam_visagesoul.so
rm -f /usr/lib/security/pam_aura_auth.so
rm -f /usr/local/bin/visagesoul
rm -f /usr/local/bin/visagesoul-verify
rm -f /usr/local/bin/aura
rm -f /usr/local/bin/aura-verify
rm -f /usr/share/applications/visagesoul.desktop
rm -f /usr/share/applications/aura-auth.desktop
rm -f /usr/share/polkit-1/actions/org.visagesoul.policy
rm -f /usr/share/polkit-1/actions/org.auraauth.policy
rm -rf /usr/share/visagesoul

if [ "$PURGE" = true ]; then
    echo -e "\n${BLUE}3. Purgando datos y perfiles biométricos...${NC}"
    rm -rf /etc/visagesoul
    rm -rf /etc/aura-auth
    echo -e "  ✓ Perfiles eliminados de /etc/visagesoul/"
else
    echo -e "\n${BLUE}3. Conservando perfiles en /etc/visagesoul/faces/ para futuras instalaciones.${NC}"
fi

echo -e "\n${GREEN}=======================================================${NC}"
echo -e "${GREEN}   ✨ ¡VisageSoul ha sido desinstalado correctamente!   ${NC}"
echo -e "${GREEN}   El sistema ha vuelto a su autenticación original.  ${NC}"
echo -e "${GREEN}=======================================================${NC}\n"
