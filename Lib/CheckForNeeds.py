import logging
import os

from arcpy import AddFieldDelimiters, ListFields, ListFeatureClasses, ListDatasets, env, Point, PointGeometry
from arcpy.da import InsertCursor, UpdateCursor, Editor, SearchCursor

from Exceptions import *
from ToolLogging import critical_info
from config.config import Config

config = Config()


def log():
    critical_info()
    error_logging = logging.getLogger('ARGADD_errors.main.CheckForNeeds')
    return error_logging

# TODO add exception handling and logging
class NewNeed(object):
    def __init__(self, shape, rpsuid, rpuid, feature_type, installation, manual_entry=False, username="Auto"):
        self.log = log()
        self.shape = shape
        self.rpsuid = rpsuid
        self.rpuid = rpuid
        self.ft = feature_type
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
                fields = ["SHAPE@", "rpsuid", "rpuid", "Feature_Type", "manual_entry", "installation", "username"]
                attributes = [self.shape, self.rpsuid, self.rpuid, self.ft, self.m_e, self.inst, self.username]
                print attributes
                with UpdateCursor(self.out_table, fields,
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
                        with InsertCursor(self.out_table, fields) as c:
                            c.insertRow(attributes)
                return True
            except Exception as e:
                self.log.exception(e)
                raise Exit()


class HQIIS(object):
    def __init__(self, usar_data):
        self.log = log()
        self.dashboard_db = config["dashboard_database"]
        self.hqiis = self.dashboard_db + os.sep + config["hqiis"]
        self.current_use_catcode_table = self.dashboard_db + os.sep + config["catcodes"]
        self.sites = self.dashboard_db + os.sep + config["sites"]
        self.usar_data = usar_data
        env.workspace = self.usar_data
        self.feature_classes = set()
        for ds in ListDatasets():
            for fc in ListFeatureClasses(feature_dataset=ds):
                self.feature_classes.add(fc)

    def curse(self):
        with SearchCursor(self.hqiis, ["INSTALLATION_CODE", "SITE_UID", "RPA_UID", "RPA_PREDOMINANT_CURRENT_USE_CAT"]) as cursor:
            for r in cursor:
                fcs = self.__is_applicable(r[3])
                if not fcs:
                    continue
                if not self.__check_exist_in_db(r[2], fcs):
                    ft = fcs[0]
                    shape = self.__lookup_geometry(r[1])
                    if not shape:
                        gen_point = Point(0, 0, 0)
                        shape = PointGeometry(gen_point)
                        self.log.info(str(r[1]) + " not in 'Site' layer.")
                    need = NewNeed(shape, r[1], r[2], ft, r[0])
                    need.push()
                    del need
                else:
                    print "miss: " + str(r[2])

    def __check_exist_in_db(self, rpuid, fc_list):
        """

        :type fc_list: list
        """
        new_fc_list = list(fc_list)

        for fc in self.feature_classes:
            if new_fc_list:
                fc_name = fc.split('.')[-1]
                if fc_name in new_fc_list or fc_name[:-2] in new_fc_list:
                    try:
                        new_fc_list.remove(fc_name)
                    except ValueError:
                        try:
                            new_fc_list.remove(fc_name[:-2])
                        except ValueError:
                            pass
                    fields = [f.name for f in ListFields(fc)]
                    if "rpuid" in fields:
                        rpauid_f = AddFieldDelimiters(fc, "rpuid")
                        with SearchCursor(fc, ["rpuid"], where_clause="{0}='{1}'".format(rpauid_f, str(rpuid))) as c:
                            for _ in c:
                                return True
        return False

    def __lookup_geometry(self, rpsuid):
        """

        :rtype: geometry object
        """
        rpsuid_sites_f = AddFieldDelimiters(self.sites, "rpsuid")
        with SearchCursor(self.sites, ["SHAPE@", "RPSUID"], where_clause="{0}='{1}'".format(rpsuid_sites_f, rpsuid)) as cur:
            for r in cur:
                return r[0]
        return False

    def __is_applicable(self, catcode):
        """

        :rtype: list
        """
        ccodes_f = AddFieldDelimiters(self.current_use_catcode_table, "RPA_PREDOMINANT_CURRENT_USE_CAT")
        with SearchCursor(self.current_use_catcode_table, ["CIP", "Army_CIP_Priority_1", "Feature_Type"],
                          where_clause="{0}='{1}'".format(ccodes_f, catcode)) as curs:
            for r in curs:
                if str(r[0]) == '1' or str(r[1]) == '1':
                    return list(r[2].split(', '))
        return False
