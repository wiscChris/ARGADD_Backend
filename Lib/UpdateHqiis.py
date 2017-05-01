from arcpy import ExcelToTable_conversion, env

from config.config import Config

# TODO map input to somewhere
raw_hqiis = ""
hqiis_location = Config()["database_connection_path"] + "\\HQIIS"

env.overwriteOutput = True

try:
    ExcelToTable_conversion(raw_hqiis, hqiis_location)
except:
    # TODO implement error catching
    pass

env.overwriteOutput = False
