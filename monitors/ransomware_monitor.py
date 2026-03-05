"""
monitors/ransomware_monitor.py
Módulo Anti-Ransomware.
A) Detección por tasa de escritura usando inotify:
   Vigila /home y /tmp; detecta ráfagas masivas de cambios en pocos segundos.
B) Detección por extensiones sospechosas.
C) Acción de emergencia: kill -STOP al PID sospechoso + LOCKDOWN.
"""

import os
import signal
import time
import threading
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional
import psutil

try:
    import inotify_simple
    INOTIFY_AVAILABLE = True
except ImportError:
    INOTIFY_AVAILABLE = False

import config.config as cfg
from config.config import (
    MONITOR_DIRS,
    RANSOMWARE_EXTENSIONS,
    INOTIFY_BURST_WINDOW,
    INOTIFY_BURST_THRESHOLD,
)
from logs.logger import logger
from utils.alerts import alert_critical, alert_lockdown, alert_warning, alert_info


class RansomwareMonitor:
    """
    Monitor anti-ransomware que combina:
    - Detección por inotify (ráfagas de escritura en tiempo real).
    - Detección por extensiones de archivo sospechosas.
    - Activación de LOCKDOWN y suspensión (SIGSTOP) del proceso sospechoso.
    """

    def __init__(self):
        self._running = False
        # Ventana deslizante de eventos por directorio: {dir: deque de timestamps}
        self._event_timestamps: dict = defaultdict(deque)
        self._lock = threading.Lock()

        logger.info(
            "RansomwareMonitor inicializado. Directorios vigilados: %s | "
            "Extensiones sospechosas: %s",
            MONITOR_DIRS,
            RANSOMWARE_EXTENSIONS,
        )

    # ──────────────────────────────────────────────────────────────────
    # A) Detección por inotify (tasa de escritura)
    # ──────────────────────────────────────────────────────────────────

    def _setup_inotify(self) -> Optional[object]:
        """
        Configura inotify para vigilar los directorios objetivo.
        Retorna el objeto inotify o None si no está disponible.
        """
        if not INOTIFY_AVAILABLE:
            logger.warning(
                "inotify_simple no disponible. Instalá con: pip install inotify-simple"
            )
            return None

        inotify = inotify_simple.INotify()
        flags = (
            inotify_simple.flags.CREATE |
            inotify_simple.flags.MODIFY |
            inotify_simple.flags.MOVED_TO |
            inotify_simple.flags.CLOSE_WRITE
        )

        for directory in MONITOR_DIRS:
            if os.path.isdir(directory):
                try:
                    # Vigilar el directorio y sus subdirectorios (nivel 1)
                    inotify.add_watch(directory, flags)
                    # Agregar subdirectorios existentes
                    for entry in os.scandir(directory):
                        if entry.is_dir(follow_symlinks=False):
                            try:
                                inotify.add_watch(entry.path, flags)
                            except PermissionError:
                                pass
                    logger.info("inotify: vigilando '%s'", directory)
                except PermissionError as e:
                    logger.error("inotify: sin permisos en '%s': %s", directory, e)
            else:
                logger.warning("inotify: directorio '%s' no existe.", directory)

        return inotify

    def _check_burst(self, watch_dir: str, event_name: str) -> bool:
        """
        Registra el evento en la ventana deslizante y verifica si
        se supera el umbral de ráfaga dentro de INOTIFY_BURST_WINDOW segundos.
        Retorna True si se detecta ráfaga.
        """
        now = time.time()
        with self._lock:
            dq = self._event_timestamps[watch_dir]
            dq.append(now)
            # Eliminar eventos fuera de la ventana temporal
            while dq and now - dq[0] > INOTIFY_BURST_WINDOW:
                dq.popleft()
            count = len(dq)

        if count >= INOTIFY_BURST_THRESHOLD:
            logger.warning(
                "RÁFAGA DETECTADA: %d eventos en %ds en '%s' (evento: '%s')",
                count, INOTIFY_BURST_WINDOW, watch_dir, event_name,
            )
            return True
        return False

    # ──────────────────────────────────────────────────────────────────
    # B) Detección por extensiones sospechosas
    # ──────────────────────────────────────────────────────────────────

    def _is_suspicious_extension(self, filename: str) -> bool:
        """Verifica si el archivo tiene una extensión de ransomware conocida."""
        suffix = Path(filename).suffix.lower()
        return suffix in RANSOMWARE_EXTENSIONS

    def _find_pid_for_path(self, filepath: str) -> Optional[int]:
        """
        Intenta encontrar el PID del proceso que tiene abierto 'filepath'.
        Utiliza lsof-like vía psutil.
        """
        for proc in psutil.process_iter(["pid", "open_files", "name"]):
            try:
                for f in proc.open_files():
                    if f.path == filepath:
                        return proc.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return None

    # ──────────────────────────────────────────────────────────────────
    # C) Acción de emergencia
    # ──────────────────────────────────────────────────────────────────

    def _emergency_action(self, pid: Optional[int], reason: str) -> None:
        """
        Acción de emergencia ante detección de ransomware:
        1. Si se conoce el PID: envía SIGSTOP para suspender el proceso.
        2. Activa modo LOCKDOWN global.
        3. Registra evento crítico.
        """
        # Activar LOCKDOWN global
        cfg.LOCKDOWN = True
        msg_lock = f"MODO LOCKDOWN ACTIVADO — Razón: {reason}"
        alert_lockdown(msg_lock)
        logger.critical("RANSOMWARE LOCKDOWN: %s", msg_lock)

        # Suspender proceso sospechoso
        if pid is not None:
            try:
                logger.critical(
                    "RANSOMWARE: Enviando SIGSTOP a PID:%d", pid
                )
                alert_critical(f"Enviando SIGSTOP al proceso sospechoso PID:{pid}")
                os.kill(pid, signal.SIGSTOP)
                logger.critical("SIGSTOP aplicado a PID:%d", pid)

                # Registrar información del proceso
                try:
                    proc = psutil.Process(pid)
                    logger.critical(
                        "Proceso suspendido → PID:%d nombre:'%s' usuario:'%s' cmd:%s",
                        pid, proc.name(), proc.username(), proc.cmdline(),
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            except ProcessLookupError:
                logger.warning("PID:%d no encontrado al enviar SIGSTOP.", pid)
            except PermissionError:
                logger.error("Sin permisos para SIGSTOP a PID:%d", pid)
        else:
            alert_critical("RANSOMWARE detectado pero PID desconocido. LOCKDOWN activo.")
            logger.critical("RANSOMWARE: PID desconocido. LOCKDOWN activo.")

    # ──────────────────────────────────────────────────────────────────
    # Bucle principal de inotify
    # ──────────────────────────────────────────────────────────────────

    def _inotify_loop(self) -> None:
        """
        Bucle principal que procesa eventos de inotify en un hilo separado.
        Evalúa cada evento por extensión y por tasa de escritura.
        """
        inotify = self._setup_inotify()
        if inotify is None:
            logger.warning("RansomwareMonitor: modo fallback (sin inotify). Solo detección por barrido.")
            return

        logger.info("RansomwareMonitor: bucle inotify iniciado.")

        # Mapeo de watch descriptor a ruta
        wd_to_path: dict = {}
        for directory in MONITOR_DIRS:
            if os.path.isdir(directory):
                try:
                    wd = inotify.add_watch(directory, inotify_simple.flags.CREATE)
                    wd_to_path[wd] = directory
                except Exception:
                    pass

        while self._running:
            if cfg.LOCKDOWN:
                # Durante LOCKDOWN no se procesan nuevos eventos de escritura
                time.sleep(1)
                continue

            try:
                events = inotify.read(timeout=1000)  # 1 segundo de timeout
            except Exception as e:
                logger.error("inotify.read() error: %s", e)
                break

            for event in events:
                if cfg.LOCKDOWN:
                    break

                filename = event.name if hasattr(event, "name") else ""
                watch_dir = wd_to_path.get(event.wd, "desconocido")
                filepath  = os.path.join(watch_dir, filename)

                # B) Verificar extensión sospechosa
                if filename and self._is_suspicious_extension(filename):
                    logger.critical(
                        "RANSOMWARE: extensión sospechosa detectada → '%s' en '%s'",
                        filename, watch_dir,
                    )
                    alert_critical(
                        f"Extensión sospechosa: '{filename}' en '{watch_dir}'"
                    )
                    pid = self._find_pid_for_path(filepath)
                    self._emergency_action(pid, f"extensión sospechosa '{Path(filename).suffix}'")

                # A) Verificar ráfaga de escritura
                if filename and self._check_burst(watch_dir, filename):
                    alert_critical(
                        f"RÁFAGA DE ESCRITURA detectada en '{watch_dir}' "
                        f"({INOTIFY_BURST_THRESHOLD} eventos/{INOTIFY_BURST_WINDOW}s)"
                    )
                    pid = self._find_pid_for_path(filepath)
                    self._emergency_action(pid, "ráfaga masiva de escritura")

        logger.info("RansomwareMonitor: bucle inotify finalizado.")

    # ──────────────────────────────────────────────────────────────────
    # Barrido de extensiones (modo fallback y complementario)
    # ──────────────────────────────────────────────────────────────────

    def scan_suspicious_files(self) -> None:
        """
        Barrido complementario de los directorios vigilados para detectar
        archivos con extensiones sospechosas ya existentes.
        Se ejecuta periódicamente o como fallback si inotify no está disponible.
        """
        if cfg.LOCKDOWN:
            return

        for directory in MONITOR_DIRS:
            if not os.path.isdir(directory):
                continue
            try:
                for root, dirs, files in os.walk(directory):
                    for fname in files:
                        if self._is_suspicious_extension(fname):
                            full_path = os.path.join(root, fname)
                            logger.critical(
                                "RANSOMWARE BARRIDO: archivo sospechoso → '%s'", full_path
                            )
                            alert_critical(f"Archivo sospechoso encontrado: '{full_path}'")
                            pid = self._find_pid_for_path(full_path)
                            self._emergency_action(
                                pid, f"archivo sospechoso encontrado en barrido: '{full_path}'"
                            )
                            return  # Una detección es suficiente para activar lockdown
            except PermissionError as e:
                logger.warning("Barrido: sin acceso a '%s': %s", directory, e)

    # ──────────────────────────────────────────────────────────────────
    # Inicio y parada
    # ──────────────────────────────────────────────────────────────────

    def start(self) -> threading.Thread:
        """
        Inicia el monitor en un hilo daemon separado para no bloquear
        el hilo principal.
        Retorna el objeto Thread para que el llamador pueda unirse si lo desea.
        """
        self._running = True
        thread = threading.Thread(
            target=self._inotify_loop,
            name="RansomwareMonitor-inotify",
            daemon=True,
        )
        thread.start()
        logger.info("RansomwareMonitor iniciado en hilo '%s'.", thread.name)
        return thread

    def stop(self) -> None:
        """Detiene el bucle de inotify."""
        self._running = False
        logger.info("RansomwareMonitor: señal de parada enviada.")