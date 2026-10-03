import logging

from pythonjsonlogger.json import JsonFormatter


def get_logger(name:str) -> logging.Logger:
    logger = logging.getLogger(name) 
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.terminator = "\n\n"
        formatter = JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s %(filename)s %(funcName)s" )
        handler.setFormatter(formatter) 
        logger.addHandler(handler)
        logger.setLevel("INFO")

    return logger

