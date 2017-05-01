import logging

from arcpy import AcceptConnections, Exists

from Lib import KickUsers, ToolLogging, CheckForNeeds
from Lib.Exceptions import *
from config.config import Config

config = Config()


def main():
    def log():
        ToolLogging.critical_info()
        error_logging = logging.getLogger('ARGADD_errors.main.main')
        return error_logging
    log = log()

    dashboard_db = config["dashboard_database"]
    usar_data = config["in_data"]
    try:
        if not Exists(usar_data):
            raise InaccessibleData("Usar input data is not accessible.")
        AcceptConnections(dashboard_db, False)
        KickUsers.kick(dashboard_db)
        # TODO turned off for debugging other modules
        # CheckFieldQuality.FieldAnalysis(usar_data)
        CheckForNeeds.HQIIS(usar_data)
    except InaccessibleData as e:
        log.exception(e.message)
    except Exit:
        pass
    except Exception as e:
        log.exception(e)
    else:
        if ToolLogging.complete_run():
            complete_logger = logging.getLogger('ARGADD_complete.main.main')
            complete_logger.info('All tasks finished successfully.')
    finally:
        # noinspection PyBroadException
        try:
            AcceptConnections(dashboard_db, True)
        except:
            log.error("SDE Connection may not accept connections.")

main()
