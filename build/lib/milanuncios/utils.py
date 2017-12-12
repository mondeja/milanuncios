#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Utils module"""

import logging

DEFAULT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s:%(lineno)d: %(message)s"
DEFAULT_FORMATTER = logging.Formatter(DEFAULT_FORMAT)

def create_logger(name, level=logging.INFO, handler=logging.StreamHandler(),
                  propagate=True):
    """Devuelve un logger con nombre, nivel y manejador provistos."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler.setFormatter(DEFAULT_FORMATTER)
    logger.addHandler(handler)
    logger.propagate = propagate
    return logger
