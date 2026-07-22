"""Configuración centralizada de logging para toda la aplicación."""

import logging

LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging(log_file: str = "", level: int = logging.INFO) -> None:
    """Configura el logger raíz con salida a consola y opcionalmente a archivo.

    Args:
        log_file: Ruta del archivo de log; si está vacío solo loguea a consola.
        level: Nivel mínimo de logging.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(level=level, format=LOGGING_FORMAT, handlers=handlers, force=True)
