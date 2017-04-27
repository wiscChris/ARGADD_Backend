from config.config import Config
from datetime import datetime
from arcpy import AcceptConnections
from Lib import Kick_users, tool_logging, check_quality
from Lib.Exceptions import DBLock
import logging


config = Config()

def main():
    def error_log():
        tool_logging.critical_errors()
        error_logging = logging.getLogger('ARGADD_errors.main.main')
        return error_logging

    def info_log():
        tool_logging.information()
        info_logging = logging.getLogger('ARGADD_info.main.main')
        return info_logging
    dashboard_db = config["dashboard_database"]
    usar_data = config["in_data"]
    try:
        AcceptConnections(dashboard_db, False)
        Kick_users.kick(dashboard_db)
        check_quality.FieldAnalysis(usar_data)

    except DBLock as e:
        error_log().error(e.message)
    except Exception as e:
        # TODO make exceptions less vague
        error_log().exception(e)
    else:
        if tool_logging.complete_run():
            complete_logger = logging.getLogger('ARGADD_complete.main.main')
            complete_logger.info('All tasks finished successfully.')
    finally:
        try:
            AcceptConnections(dashboard_db, True)
        except:
            error_log().error("SDE Connection may not accept connections.")

main()
