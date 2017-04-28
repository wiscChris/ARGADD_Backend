from config.config import Config
from arcpy import AcceptConnections, Exists
from Lib import Kick_users, tool_logging, check_quality
from Lib.Exceptions import *
import logging


config = Config()


def main():
    def log():
        tool_logging.critical_info()
        error_logging = logging.getLogger('ARGADD_errors.main.main')
        return error_logging
    log = log()

    dashboard_db = config["dashboard_database"]
    usar_data = config["in_data"]
    try:
        if not Exists(usar_data):
            raise InaccessibleData("Usar input data is not accessible.")
        AcceptConnections(dashboard_db, False)
        Kick_users.kick(dashboard_db)
        check_quality.FieldAnalysis(usar_data)
    except InaccessibleData as e:
        log.exception(e.message)
    except DBLock as e:
        log.exception(e.message)
    except Exception as e:
        log.exception(e)
    else:
        if tool_logging.complete_run():
            complete_logger = logging.getLogger('ARGADD_complete.main.main')
            complete_logger.info('All tasks finished successfully.')
    finally:
        # noinspection PyBroadException
        try:
            AcceptConnections(dashboard_db, True)
        except:
            log.error("SDE Connection may not accept connections.")

main()
