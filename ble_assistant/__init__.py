"""
@author: qiudeliang
"""

from .log import setup_logging, setup_dongle_log, setup_serial_log
from .config import settings

__version__ = '0.0.1'

logger = setup_logging()
dongle_logger = setup_dongle_log(settings.DONGLE_LOG_NAME)
serial_logger = setup_serial_log(settings.SERIAL_LOG_NAME)
