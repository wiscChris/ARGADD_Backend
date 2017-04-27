import os
import logging
from datetime import datetime
from config.config import Config

__time_now = datetime.now()

log_directory = Config()["logs_directory"]
__error_folder = log_directory + os.sep + "Errors"
__complete_folder = log_directory + os.sep + "Completed"
__info_folder = log_directory + os.sep + "Information"
log_folder_dir_list = [__error_folder, __info_folder, __complete_folder]

for lf in log_folder_dir_list:
    try:
        os.mkdir(lf)
    except OSError:
        pass


def critical_errors():
    logger = logging.getLogger('ARGADD_errors')
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(
        filename=__error_folder + os.sep + str(__time_now.year) + str(__time_now.month) + str(__time_now.day) + ".log")

    ch = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return True


def information():
    logger = logging.getLogger('ARGADD_info')
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(
        filename=__info_folder + os.sep + str(__time_now.year) + str(__time_now.month) + str(__time_now.day) + ".log")

    ch = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return True


def complete_run():
    logger = logging.getLogger('ARGADD_complete')
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(
        filename=__complete_folder + os.sep + str(__time_now.year) + str(__time_now.month) + str(__time_now.day) + ".log")

    ch = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return True
