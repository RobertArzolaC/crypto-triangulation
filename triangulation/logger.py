"""Configuración centralizada de logging para toda la aplicación."""

import logging
from logging.handlers import RotatingFileHandler

LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

MAX_LOG_BYTES = 5_000_000
LOG_BACKUP_COUNT = 3


def setup_logging(log_file: str = "", level: int = logging.INFO) -> None:
    """Configura el logger raíz con salida a consola y archivo rotativo.

    Args:
        log_file: Ruta del archivo de log; si está vacío solo loguea a consola.
            El archivo rota al llegar a 5 MB y conserva 3 respaldos.
        level: Nivel mínimo de logging.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(
            RotatingFileHandler(
                log_file,
                maxBytes=MAX_LOG_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
        )
    logging.basicConfig(level=level, format=LOGGING_FORMAT, handlers=handlers, force=True)
