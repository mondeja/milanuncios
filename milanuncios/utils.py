#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Utils module"""

import logging
import datetime

DEFAULT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s:%(lineno)d: %(message)s"
DEFAULT_FORMATTER = logging.Formatter(DEFAULT_FORMAT)

def create_logger(name, level=logging.INFO, handler=logging.StreamHandler(),
                  propagate=True):
    """Returns a logger with given name, level and handler."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler.setFormatter(DEFAULT_FORMATTER)
    logger.addHandler(handler)
    logger.propagate = propagate
    return logger

def extract_number(string, parse):
    """Returns a number from a string parsing it with a given type"""
    response = ""
    for char in string:
        if char.isdigit():
            response += char
    return parse(response)

def parse_string_to_timedelta(string):
    """Convert a string in the form "4 horas" to timedelta object"""
    string_mapping = {"horas": "hours",
                      "hora": "hours",
                      "días": "days",
                      "día": "days",
                      "dia": "days",
                      "dias": "days",
                      "seg": "seconds",
                      "min": "minutes"}
    num = extract_number(string, int)
    for inp, outp in string_mapping.items():
        if inp in string:
            arg = outp
            break
    kwarg = {arg: num}
    return datetime.timedelta(**kwarg)
