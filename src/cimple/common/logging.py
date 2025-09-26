import logging
import os

logger = logging.getLogger("cimple")
if "CIMPLE_DEBUG" in os.environ and os.environ["CIMPLE_DEBUG"] != "":
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def debug(msg: str, *args: object):
    logger.debug(msg, *args)


def info(msg: str, *args: object):
    logger.info(msg, *args)


def warning(msg: str, *args: object):
    logger.warning(msg, *args)


def error(msg: str, *args: object):
    logger.error(msg, *args)
