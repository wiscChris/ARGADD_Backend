import logging

from arcpy import AcceptConnections

from Lib import KickUsers, ToolLogging, CheckForNeeds
from Lib.Exceptions import *
from config.config import Config, CheckConfig

config = Config()


def main():
    def log():
        ToolLogging.critical_info()
        error_logging = logging.getLogger('ARGADD_errors.main.main')
        return error_logging
    log = log()


    try:
        CheckConfig()

        # Set params
        dashboard_db = config["dashboard_database"]
        usar_data = config["in_data"]

        # Prepare database for editing
        AcceptConnections(dashboard_db, False)
        KickUsers.kick(dashboard_db)

        # Do analysis
        # TODO turned off for debugging other modules
        # CheckFieldQuality.FieldAnalysis(usar_data)

        needs_check = CheckForNeeds.HQIIS(usar_data)
        needs_check.curse()

    except Exit:
        log.exception("Critical Error occured. Tools did not complete. Check log!")
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
