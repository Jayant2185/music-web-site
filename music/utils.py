import logging
from logging.config import fileConfig

fileConfig('log_config.ini')
logger = logging.getLogger()
logger.debug('the best scripting language is python in the world')