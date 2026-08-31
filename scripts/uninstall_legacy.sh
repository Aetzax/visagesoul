#!/usr/bin/env bash
# ==============================================================================
# VisageSoul: Script de Limpieza y Desinstalación de la versión anterior (AuraAuth)
# ==============================================================================
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}   🧹 Limpieza y Desinstalación del viejo AuraAuth     ${NC}"
echo -e "${BLUE}=======================================================${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Solicitando permisos de administrador (sudo)...${NC}"
    exec sudo bash "$0" "$@"
fi

echo -e "\n1. Limpiando referencias viejas de PAM en /etc/pam.d/..."
for pam_file in /etc/pam.d/*; do
    if [ -f "$pam_file" ] && grep -q "pam_aura_auth.so" "$pam_file" 2>/dev/null; then
        echo "  -> Limpiando $pam_file..."
        sed -i '/pam_aura_auth.so/d' "$pam_file"
    fi
done

echo -e "\n2. Migrando perfiles de rostro a VisageSoul (si existen)..."
mkdir -p /etc/visagesoul/faces
if [ -d "/etc/aura-auth/faces" ]; then
    cp -n /etc/aura-auth/faces/*.json /etc/visagesoul/faces/ 2>/dev/null || true
    echo "  ✓ Perfiles migrados a /etc/visagesoul/faces/"
fi

echo -e "\n3. Eliminando archivos y carpetas del viejo AuraAuth..."
rm -rf /opt/aura-auth
rm -f /usr/lib/security/pam_aura_auth.so
rm -f /usr/share/applications/aura-auth.desktop
rm -f /usr/share/polkit-1/actions/org.auraauth.policy
rm -rf /etc/aura-auth
rm -f /usr/local/bin/aura-verify

echo -e "\n${GREEN}=======================================================${NC}"
echo -e "${GREEN}   ✨ ¡El viejo AuraAuth ha sido eliminado por completo! ${NC}"
echo -e "${GREEN}   El sistema ha quedado 100% limpio para VisageSoul.   ${NC}"
echo -e "${GREEN}=======================================================${NC}\n"
