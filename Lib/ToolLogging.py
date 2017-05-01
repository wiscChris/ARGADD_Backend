import logging
import os
from datetime import datetime

from config.config import Config

__time_now = datetime.now()

log_directory = Config()["logs_directory"]
__error_folder = log_directory + os.sep + "Errors"
__complete_folder = log_directory + os.sep + "Completed"
log_folder_dir_list = [__error_folder, __complete_folder]

for lf in log_folder_dir_list:
    try:
        os.mkdir(lf)
    except OSError:
        pass

loggers = {}

def critical_info():
    global loggers

    logger_name = 'ARGADD_errors'

    if loggers.get(logger_name):
        return True
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(
        filename=__error_folder + os.sep + str(__time_now.year) + str(__time_now.month) + str(__time_now.day) + ".log")

    ch = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(fh)
        logger.addHandler(ch)

    logger.propagate = False
    loggers.update(dict(name=logger_name))

    return True


def complete_run():
    global loggers

    logger_name = 'ARGADD_complete'

    if loggers.get(logger_name):
        return True

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(
        filename=__complete_folder + os.sep + str(__time_now.year) + str(__time_now.month) + str(__time_now.day) + ".log")

    ch = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    loggers.update(dict(name=logger_name))
    return True
