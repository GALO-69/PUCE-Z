# MONITOR DE RECURSOS DEL SISTEMA — SISTEMAS OPERATIVOS

Sistema de monitoreo completo para Linux Ubuntu desarrollado en Python 3.10+.
Requiere privilegios de **root** para acceder a `/proc`, `/var/log` y gestionar procesos del sistema.

---

## Índice

1. [Descripción del Sistema](#descripción-del-sistema)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Diagrama de Flujo](#diagrama-de-flujo-textual)
4. [Instalación](#instalación)
5. [Configuración de Permisos](#configuración-de-permisos)
6. [Cómo Ejecutarlo](#cómo-ejecutarlo)
7. [Configuración de Cron](#configuración-de-cron)
8. [Simulación y Pruebas](#simulación-y-pruebas)
9. [Protocolo LOCKDOWN](#protocolo-lockdown)
10. [Log del Sistema](#log-del-sistema)

---

## Descripción del Sistema

El **Monitor de Recursos del Sistema** es una herramienta de administración para Ubuntu Linux que implementa:

| Módulo | Función |
|--------|---------|
| `ResourceMonitor` | Monitorea CPU, RAM y Disco. Umbral crítico: 85% |
| `ProcessManager` | Termina procesos que superen el 70% de CPU (SIGTERM → SIGKILL) |
| `RansomwareMonitor` | Detecta comportamiento ransomware por inotify y extensiones sospechosas |
| `SystemCleaner` | Limpieza automática: /tmp, logs, apt, papelera, actualizaciones |
| `roles` | Verifica ejecución como root |
| `logger` | Registro centralizado en `/var/log/system_monitor.log` |
| `alerts` | Alertas visuales coloreadas en consola |

---

## Estructura del Proyecto

```
system_monitor/
│
├── config/
│   └── config.py              → Umbrales, rutas, listas blancas, extensiones
│
├── controllers/
│   └── system_cleaner.py      → Limpieza automática del sistema
│
├── monitors/
│   ├── resource_monitor.py    → CPU / RAM / Disco
│   ├── process_manager.py     → Gestión reactiva de procesos pesados
│   └── ransomware_monitor.py  → Anti-ransomware (inotify + extensiones)
│
├── auth/
│   └── roles.py               → Verificación de privilegios root
│
├── logs/
│   └── logger.py              → Logger centralizado (consola + archivo)
│
├── utils/
│   └── alerts.py              → Alertas visuales ANSI en consola
│
├── main.py                    → Punto de entrada principal
├── requirements.txt           → Dependencias Python
└── README.md                  → Este archivo
```

---

## Diagrama de Flujo Textual

```
INICIO
  │
  ├─► Verificar root (auth/roles.py)
  │       └─ No es root → ERROR + EXIT
  │
  ├─► ¿Argumento --clean?
  │       ├─ SÍ → SystemCleaner.run_full_cleanup() → FIN
  │       └─ NO → Continuar con monitoreo
  │
  ├─► Iniciar RansomwareMonitor en hilo separado
  │       ├─ Configurar inotify en /home y /tmp
  │       └─ Bucle de eventos:
  │               ├─ Extensión sospechosa (.locked, .enc, ...) → EMERGENCY
  │               └─ Ráfaga > 50 eventos / 10s → EMERGENCY
  │                       └─ EMERGENCY: kill -STOP PID + LOCKDOWN=True
  │
  └─► BUCLE PRINCIPAL (cada 5 segundos)
          │
          ├─► ResourceMonitor.check_once()
          │       ├─ CPU > 85%? → LOG CRÍTICO + ALERTA + usuario del proceso
          │       ├─ RAM > 85%? → LOG CRÍTICO + ALERTA
          │       └─ DISCO > 85%? → LOG CRÍTICO + ALERTA
          │
          ├─► ¿LOCKDOWN activo?
          │       ├─ SÍ → Omitir gestión de procesos
          │       └─ NO → ProcessManager.check_and_manage()
          │                   ├─ Proceso > 70% CPU?
          │                   │       ├─ ¿Lista blanca? → Ignorar
          │                   │       └─ NO → kill -15 → esperar 5s
          │                   │                   └─ ¿Sigue vivo? → kill -9
          │                   └─ LOG de todo
          │
          ├─► (cada 6 ciclos) RansomwareMonitor.scan_suspicious_files()
          │
          └─► Esperar MONITOR_INTERVAL → volver al inicio del bucle
                  │
                  └─► SIGINT/SIGTERM → Apagado ordenado → FIN
```

---

## Instalación

### Requisitos previos

```bash
# Ubuntu 20.04 / 22.04 / 24.04
sudo apt update
sudo apt install python3 python3-pip -y
```

### Clonar / descargar el proyecto

```bash
# Copiar la carpeta system_monitor a tu directorio de trabajo
cd /opt   # o cualquier directorio
# Pega/copia aquí la carpeta system_monitor/
```

### Instalar dependencias Python

```bash
cd /opt/system_monitor
sudo pip3 install -r requirements.txt
```

---

## Configuración de Permisos

Para mayor seguridad, el script principal debe pertenecer a root y solo ser ejecutable por root:

```bash
sudo chown root:root /opt/system_monitor/main.py
sudo chmod 700 /opt/system_monitor/main.py

# Opcionalmente, proteger todo el directorio:
sudo chown -R root:root /opt/system_monitor/
sudo chmod -R 700 /opt/system_monitor/
```

Crear el archivo de log con permisos correctos:

```bash
sudo touch /var/log/system_monitor.log
sudo chmod 640 /var/log/system_monitor.log
sudo chown root:adm /var/log/system_monitor.log
```

---

## Cómo Ejecutarlo

### Modo monitoreo continuo (principal)

```bash
cd /opt/system_monitor
sudo python3 main.py
```

Salida esperada:
```
╔══════════════════════════════════════════════════════════════╗
║       MONITOR DE RECURSOS DEL SISTEMA — SISTEMAS OPERATIVOS  ║
╚══════════════════════════════════════════════════════════════╝

[INFO]    2024-01-15 10:30:00 → Verificación de roles: ejecutando como root ✓
[INFO]    2024-01-15 10:30:00 → Anti-ransomware activo
[INFO]    2024-01-15 10:30:00 → Ciclo #1 — usuario real: tuUsuario
[INFO]    2024-01-15 10:30:01 → CPU: 12.3% | RAM: 45.1% (3.61GB / 8.00GB) | DISCO: 62.0% (74.4GB / 120.0GB)
```

Para detener: `Ctrl+C`

### Modo limpieza manual

```bash
sudo python3 main.py --clean
```

### Ver ayuda

```bash
sudo python3 main.py --help
```

---

## Configuración de Cron

Para ejecutar la limpieza automáticamente todos los días a las 3:00 AM:

```bash
sudo crontab -e
```

Agregar la siguiente línea:

```cron
# Limpieza automática del sistema — 3:00 AM diariamente
0 3 * * * /usr/bin/python3 /opt/system_monitor/main.py --clean >> /var/log/system_cleaner_cron.log 2>&1
```

Verificar que el cron está registrado:

```bash
sudo crontab -l
```

Para ejecutar el monitoreo continuo como servicio systemd (recomendado para producción):

```bash
# Crear archivo de servicio
sudo tee /etc/systemd/system/system-monitor.service > /dev/null <<EOF
[Unit]
Description=Monitor de Recursos del Sistema
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/system_monitor
ExecStart=/usr/bin/python3 /opt/system_monitor/main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable system-monitor
sudo systemctl start system-monitor
sudo systemctl status system-monitor
```

---

## Simulación y Pruebas

### 1. Simular alta carga de CPU con `stress`

```bash
# Instalar stress
sudo apt install stress -y

# Simular carga al 100% en todos los núcleos durante 60 segundos
stress --cpu $(nproc) --timeout 60

# En otra terminal, observar el monitor:
sudo python3 main.py
# Verás alertas CRÍTICAS cuando CPU supere el 85%
# y el ProcessManager intentará terminar el proceso stress
```

### 2. Simular detección de extensiones ransomware

```bash
# Script que crea archivos con extensiones sospechosas masivamente
#!/bin/bash
echo "Simulando ransomware en /tmp/test_ransomware/"
mkdir -p /tmp/test_ransomware

for i in $(seq 1 100); do
    # Crear archivos con extensiones sospechosas
    touch "/tmp/test_ransomware/document_${i}.locked"
    touch "/tmp/test_ransomware/photo_${i}.enc"
    touch "/tmp/test_ransomware/video_${i}.crypted"
    touch "/tmp/test_ransomware/file_${i}.encrypted"
    sleep 0.05  # Pequeña pausa para simular ráfaga real
done

echo "Simulación completada."
```

Guarda como `simulate_ransomware.sh` y ejecuta:
```bash
chmod +x simulate_ransomware.sh
bash simulate_ransomware.sh
```
El monitor detectará las extensiones `.locked`, `.enc`, `.crypted`, `.encrypted`
y activará el modo **LOCKDOWN**.

### 3. Simular ráfaga masiva de escritura (detección por inotify)

```bash
# Script que genera una ráfaga de cambios de archivos
#!/bin/bash
echo "Simulando ráfaga de escritura en /tmp/burst_test/"
mkdir -p /tmp/burst_test

# Crear 60 archivos en menos de 10 segundos (supera umbral de 50)
for i in $(seq 1 60); do
    echo "data_${i}_$(date)" > "/tmp/burst_test/file_${i}.txt"
done

echo "Ráfaga completada."
```

### 4. Verificar el log

```bash
# Ver log en tiempo real
sudo tail -f /var/log/system_monitor.log

# Buscar eventos críticos
sudo grep "CRÍTICO\|LOCKDOWN\|RANSOMWARE" /var/log/system_monitor.log

# Buscar procesos terminados
sudo grep "SIGTERM\|SIGKILL\|SIGSTOP" /var/log/system_monitor.log
```

---

## Protocolo LOCKDOWN

El modo LOCKDOWN se activa automáticamente cuando:
- Se detecta una ráfaga masiva de escritura (> 50 eventos en 10 segundos).
- Se detecta un archivo con extensión de ransomware conocida.

**Efectos del LOCKDOWN:**
1. El proceso sospechoso recibe `SIGSTOP` (suspensión inmediata).
2. La variable global `cfg.LOCKDOWN = True` bloquea la gestión reactiva de procesos.
3. La limpieza automática queda pospuesta hasta que LOCKDOWN sea desactivado.
4. Todos los eventos se registran en `/var/log/system_monitor.log`.

**Para desactivar LOCKDOWN manualmente** (después de investigar):
```python
# Desde el intérprete Python o agregando al código:
import config.config as cfg
cfg.LOCKDOWN = False

# O simplemente reiniciar el monitor:
sudo python3 main.py
```

---

## Log del Sistema

Ruta: `/var/log/system_monitor.log`

Formato de cada entrada:
```
2024-01-15 10:30:00 [CRITICAL] system_monitor: RECURSO CPU: CPU al 92.3% | Proceso: 'stress' | Usuario: 'root'
2024-01-15 10:30:05 [WARNING]  system_monitor: PROCESO PESADO DETECTADO → PID:12345 nombre:'stress' CPU:95.0% usuario:'root'
2024-01-15 10:30:05 [INFO]     system_monitor: Enviando SIGTERM (kill -15) a PID:12345 'stress'
2024-01-15 10:30:10 [WARNING]  system_monitor: PID:12345 'stress' sigue activo tras SIGTERM. Enviando SIGKILL.
2024-01-15 10:30:10 [CRITICAL] system_monitor: RANSOMWARE LOCKDOWN: MODO LOCKDOWN ACTIVADO — Razón: extensión sospechosa '.locked'
```

---

## Dependencias

| Paquete | Versión mínima | Uso |
|---------|---------------|-----|
| `psutil` | 5.9.0 | Lectura de CPU, RAM, disco y procesos |
| `inotify-simple` | 1.3.5 | Vigilancia de sistemas de archivos en tiempo real |

Ambas incluidas en `requirements.txt`.

---

## Autores y Licencia

Proyecto académico — Sistemas Operativos.
Desarrollado para Ubuntu Linux con Python 3.10+.
