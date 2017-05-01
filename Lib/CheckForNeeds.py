import logging

from arcpy import AddFieldDelimiters, ListFields, ListFeatureClasses, ListDatasets, env
from arcpy.da import InsertCursor, UpdateCursor, Editor, SearchCursor

from Exceptions import *
from ToolLogging import critical_info
from config.config import Config

config = Config()


def log():
    critical_info()
    error_logging = logging.getLogger('ARGADD_errors.main.check_quality')
    return error_logging

# TODO add exception handling and logging
class NewNeed(object):
    def __init__(self, rpsuid, rpuid, feature_type, installation, manual_entry=False, username="Auto"):
        self.log = log()
        self.rpsuid = rpsuid
        self.rpuid = rpuid
        self.ft = feature_type,
        self.inst = installation
        self.m_e = manual_entry
        self.username = username
        self.db = config["dashboard_database"]
        self.out_table = "\\".join([self.db, config["needs"]])

    def push(self):
        with Editor(self.db) as _:
            try:
                rpuid_f = AddFieldDelimiters(self.out_table, "rpuid")
                me_f = AddFieldDelimiters(self.out_table, "manual_entry")
                attributes = [self.rpsuid, self.rpuid, self.ft, self.inst, self.m_e, self.username]
                with UpdateCursor(self.out_table,
                                  ["rpsuid", "rpuid", "Feature_Type", "manual_entry", "installation", "username"],
                                  where_clause="{0}='{1}' AND {2}='{3}'".format(rpuid_f,
                                                                                str(attributes[1]),
                                                                                me_f,
                                                                                str(attributes[4]))) as cursor:
                    row_count = 0
                    for _ in cursor:
                        row_count += 1
                        if row_count == 1:
                            row = attributes
                            cursor.updateRow(row)
                        else:
                            cursor.deleteRow()
                    if not row_count:
                        with InsertCursor(self.out_table,
                                          ["rpsuid", "rpuid", "Feature_Type", "manual_entry", "installation",
                                           "username"]) as c:
                            c.insertRow(attributes)
                return True
            except Exception as e:
                self.log.exception(e)
                raise Exit()


class HQIIS(object):
    def __init__(self, usar_data):
        self.hqiis = config["hqiis"]
        self.usar_data = usar_data
        env.workspace = self.usar_data

    def curse(self):
        with SearchCursor(self.hqiis, ["INSTALLATION_CODE", "SITE_UID", "RPA_UID", "RPA_PREDOMINANT_CURRENT_USE_CAT"]) as cursor:
            for r in cursor:
                if self.__look_in_db(r[2]):
                    ft = self.__lookup_feature_type(r[3])
                    need = NewNeed(r[1], r[2], ft, r[0])
                    need.push()
                    del need

    @staticmethod
    def __look_in_db(rpuid):
        for ds in ListDatasets():
            for fc in ListFeatureClasses(feature_dataset=ds):
                fields = [f.name for f in ListFields(fc)]
                if "rpuid" in fields:
                    rpauid_f = AddFieldDelimiters(fc, "rpuid")
                    with SearchCursor(fc, ["rpuid"], where_clause="{0}='{1}'".format(rpauid_f, str(rpuid))) as c:
                        for _ in c:
                            return True
        return False

    def __lookup_feature_type(self, catcode):
        # TODO return feature type
        return "Generic"
