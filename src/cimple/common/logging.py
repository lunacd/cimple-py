import logging

logger = logging.getLogger("cimple")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def info(msg: str, *args):
    logger.info(msg, *args)


def warning(msg: str, *args):
    logger.warning(msg, *args)


def error(msg: str, *args):
    logger.error(msg, *args)
