import logging
from os import path

def get_logger(name):
    out_dir = 'logs'
    filename = name + '.log'
    out_path = path.join(out_dir, filename)


    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler(out_path)
    handler.setLevel(logging.DEBUG)

    handler_format = logging.Formatter('%(asctime)s|%(levelname)s|%(message)s')
    handler.setFormatter(handler_format)

    logger.addHandler(handler)

    return logger
