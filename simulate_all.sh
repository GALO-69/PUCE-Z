#!/bin/bash
# ══════════════════════════════════════════════════════════
# SIMULACIÓN COMPLETA — Monitor de Recursos del Sistema
# Prueba: CPU, RAM, Procesos y Anti-Ransomware
# ══════════════════════════════════════════════════════════

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     SIMULACIÓN COMPLETA DEL SISTEMA          ║"
echo "║     Asegúrate de tener el monitor corriendo  ║"
echo "║     en otra terminal: sudo python3 main.py   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
sleep 2

# ── 1. MONITOR DE CPU ──────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[1/5] Estresando CPU al 100% por 30 segundos..."
echo "      El monitor debe alertar CPU > 85%"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v stress &> /dev/null; then
    stress --cpu $(nproc) --timeout 30
else
    # Simulación con Python si no hay stress
    python3 -c "
import time
end = time.time() + 30
print('Simulando carga CPU con Python...')
while time.time() < end:
    x = 99999 ** 999
"
fi
echo "[✓] CPU completado"
sleep 3

# ── 2. MONITOR DE RAM ──────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[2/5] Estresando RAM con 800MB por 20 segundos..."
echo "      El monitor debe alertar RAM > 85%"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v stress &> /dev/null; then
    stress --vm 1 --vm-bytes 800M --timeout 20
else
    python3 -c "
import time
print('Simulando carga RAM con Python...')
data = []
for i in range(50):
    data.append('x' * 1024 * 1024)
time.sleep(20)
del data
"
fi
echo "[✓] RAM completado"
sleep 3

# ── 3. GESTIÓN DE PROCESOS PESADOS ─────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[3/5] Lanzando proceso pesado de CPU..."
echo "      El ProcessManager debe enviar SIGTERM/SIGKILL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v stress &> /dev/null; then
    stress --cpu $(nproc) --timeout 25 &
    STRESS_PID=$!
    echo "      Proceso lanzado con PID: $STRESS_PID"
    sleep 25
else
    python3 -c "
import time
end = time.time() + 25
print('Proceso pesado simulado con Python...')
while time.time() < end:
    x = 99999 ** 999
" &
    sleep 25
fi
echo "[✓] Gestión de procesos completada"
sleep 3

# ── 4. ANTI-RANSOMWARE: EXTENSIONES SOSPECHOSAS ────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[4/5] Simulando archivos con extensiones ransomware..."
echo "      El RansomwareMonitor debe activar LOCKDOWN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p /tmp/test_ransomware
for i in $(seq 1 30); do
    touch "/tmp/test_ransomware/documento_${i}.locked"
    touch "/tmp/test_ransomware/foto_${i}.enc"
    touch "/tmp/test_ransomware/archivo_${i}.crypted"
    touch "/tmp/test_ransomware/video_${i}.encrypted"
    sleep 0.05
done
echo "[✓] Archivos ransomware creados en /tmp/test_ransomware/"
sleep 3

# ── 5. ANTI-RANSOMWARE: RÁFAGA DE ESCRITURA ────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[5/5] Simulando ráfaga masiva de escritura en /tmp..."
echo "      inotify debe detectar más de 50 eventos en 10s"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p /tmp/burst_test
for i in $(seq 1 80); do
    echo "data_${i}_$(date)" > "/tmp/burst_test/file_${i}.txt"
done
echo "[✓] Ráfaga de escritura completada"
sleep 2

# ── LIMPIEZA ────────────────────────────────────────────
echo ""
echo "Limpiando archivos de prueba..."
rm -rf /tmp/test_ransomware
rm -rf /tmp/burst_test
echo "[✓] Limpieza completada"

# ── RESUMEN ─────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     SIMULACIÓN FINALIZADA ✓                  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Ver log completo:"
echo "  sudo cat /var/log/system_monitor.log"
echo ""
echo "Ver solo alertas críticas:"
echo "  sudo grep CRITICAL /var/log/system_monitor.log"
echo ""
