#!/bin/bash
# ══════════════════════════════════════════════════════════
# SETUP AUTOMÁTICO — Monitor de Recursos del Sistema
# Crea __init__.py, instala dependencias y ejecuta el monitor
# ══════════════════════════════════════════════════════════

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     SETUP DEL MONITOR DE RECURSOS            ║"
echo "╚══════════════════════════════════════════════╝"

# ── Verificar root ──────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Ejecuta con sudo"
    echo "  sudo ./setup.sh"
    exit 1
fi

# ── 1. Crear __init__.py en todas las carpetas ──────────
echo ""
echo "[1/5] Creando archivos __init__.py..."
touch config/__init__.py
touch controllers/__init__.py
touch monitors/__init__.py
touch auth/__init__.py
touch logs/__init__.py
touch utils/__init__.py
echo "[✓] __init__.py creados"

# ── 2. Verificar nombres de archivos ────────────────────
echo ""
echo "[2/5] Verificando nombres de archivos..."

# monitors/
[ -f monitors/resourcemonitor.py ] && mv monitors/resourcemonitor.py monitors/resource_monitor.py && echo "    Renombrado: resource_monitor.py"
[ -f monitors/processmanager.py ]  && mv monitors/processmanager.py monitors/process_manager.py   && echo "    Renombrado: process_manager.py"
[ -f monitors/ransomware.py ]      && mv monitors/ransomware.py monitors/ransomware_monitor.py     && echo "    Renombrado: ransomware_monitor.py"

# controllers/
[ -f controllers/systemcleaner.py ] && mv controllers/systemcleaner.py controllers/system_cleaner.py && echo "    Renombrado: system_cleaner.py"

echo "[✓] Archivos verificados"

# ── 3. Instalar dependencias Python ─────────────────────
echo ""
echo "[3/5] Instalando dependencias Python..."
pip3 install -r requirements.txt --break-system-packages
echo "[✓] Dependencias instaladas"

# ── 4. Instalar stress ───────────────────────────────────
echo ""
echo "[4/5] Instalando stress..."
apt install stress -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" 2>/dev/null
if command -v stress &> /dev/null; then
    echo "[✓] stress instalado"
else
    echo "[!] stress no se pudo instalar, se usará simulación Python"
fi

# ── 5. Crear archivo de log ──────────────────────────────
echo ""
echo "[5/5] Configurando log del sistema..."
touch /var/log/system_monitor.log
chmod 640 /var/log/system_monitor.log
echo "[✓] Log configurado en /var/log/system_monitor.log"

# ── Mostrar estructura final ─────────────────────────────
echo ""
echo "Estructura del proyecto:"
echo "├── auth/        $(ls auth/)"
echo "├── config/      $(ls config/)"
echo "├── controllers/ $(ls controllers/)"
echo "├── logs/        $(ls logs/)"
echo "├── monitors/    $(ls monitors/)"
echo "├── utils/       $(ls utils/)"
echo "└── main.py"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     SETUP COMPLETADO ✓                       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Para ejecutar el monitor:"
echo "  sudo python3 main.py"
echo ""
echo "Para ejecutar la simulación:"
echo "  sudo ./simulate_all.sh"
echo ""
