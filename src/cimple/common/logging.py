import logging
import os

logger = logging.getLogger("cimple")
if "CIMPLE_DEBUG" in os.environ is not None and os.environ["CIMPLE_DEBUG"] != "":
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def debug(msg: str, *args):
    logger.debug(msg, *args)


def info(msg: str, *args):
    logger.info(msg, *args)


def warning(msg: str, *args):
    logger.warning(msg, *args)


def error(msg: str, *args):
    logger.error(msg, *args)
