#!/usr/bin/env python3
# -*-encoding: utf-8-*-
# Author: Vitalii Serhiienko

# Source: https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output

import logging

class ColoredLogFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s:%(msecs)03d %(levelname)-7s %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        datefmt = "%H:%M:%S"
        formatter = logging.Formatter(log_fmt, datefmt)
        return formatter.format(record)

log = logging.getLogger("JiraAutomation")
log.setLevel(logging.INFO)
sh = logging.StreamHandler()
sh.setFormatter(ColoredLogFormatter())
log.addHandler(sh)
