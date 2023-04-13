import logging

from constants import LOGGING_FORMAT


class CryptoLogger:

    def __init__(self, name, level=logging.INFO, file_path=None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        ch = logging.StreamHandler()
        ch.setLevel(level)

        formatter = logging.Formatter(LOGGING_FORMAT)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        if file_path is not None:
            fh = logging.FileHandler(file_path)
            fh.setLevel(level)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)
