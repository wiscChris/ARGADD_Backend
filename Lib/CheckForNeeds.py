import logging
import os

from arcpy import AddFieldDelimiters, ListFields, ListFeatureClasses, ListDatasets, env, Point, PointGeometry
from arcpy.da import InsertCursor, UpdateCursor, Editor, SearchCursor

from Cache import File
from Exceptions import *
from LayerStatus import LayerStatus
from ToolLogging import critical_info
from config.config import Config

config = Config()


def log():
    critical_info()
    error_logging = logging.getLogger('ARGADD_errors.main.CheckForNeeds')
    return error_logging


class NewNeed(object):
    def __init__(self, shape, rpsuid, rpuid, feature_type, installation, manual_entry=0, username="Auto"):
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
                with UpdateCursor(self.out_table, fields,
                                  where_clause="{0}='{1}' AND {2}='{3}'".format(rpuid_f, str(attributes[2]),
                                                                                me_f, str(attributes[4]))) as CURSOR:
                    row_count = 0
                    for _ in CURSOR:
                        row_count += 1
                        if row_count == 1:
                            row = attributes
                            CURSOR.updateRow(row)
                        else:
                            # Deletes extra rows that match the SQL clause
                            CURSOR.deleteRow()
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
        feature_types = config["feature_types"].split(", ")
        self.layer_status = LayerStatus(self.dashboard_db + os.sep + config["CIP_Layer_Status"])
        self.layer_status.baseline_the_table(self.__get_insts_sites(), feature_types)
        for ds in ListDatasets():
            for fc in ListFeatureClasses(feature_dataset=ds):
                self.feature_classes.add(fc)
        read_cache = File("CheckForNeeds")
        self.previous_rpuids = read_cache.read()

    def curse(self):
        try:
            op_status_f = AddFieldDelimiters(self.hqiis, "OPERATIONAL_STATUS_NAME")
            type_f = AddFieldDelimiters(self.hqiis, "RPA_TYPE_CODE")
            with SearchCursor(self.hqiis, ["INSTALLATION_CODE", "SITE_UID", "RPA_UID", "RPA_PREDOMINANT_CURRENT_USE_CAT"],
                              where_clause="{0}<>'{1}' AND {2}<>'{3}'".format(op_status_f, "Closed ", type_f, "L")) as s_cursor:
                for r in s_cursor:
                    if r[2] in self.previous_rpuids:
                        continue
                    fcs = self.__is_applicable(r[3])
                    if not fcs:
                        self.previous_rpuids.append(r[2])
                        continue
                    if not self.__check_exist_in_db(r[2], fcs):
                        self.layer_status.add_status(r[0], r[1], fcs[0], 2)
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
                        self.layer_status.add_status(r[0], r[1], fcs[0], 1)
                    self.previous_rpuids.append(r[2])
        except Exception as e:
            cache = File("CheckForNeeds", self.previous_rpuids)
            if not cache.save():
                self.log.error("Cache did not work.")
            self.layer_status.write_cache()
            self.log.exception(e.message)
            raise Exit()
        else:
            self.layer_status.post_to_table()

    def __check_exist_in_db(self, rpuid, fc_list):
        """
        Checks if the rpuid exists in the given database.
        :type fc_list: list
        """
        try:
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
        except Exception as e:
            self.log.exception(e.message)
            raise Exit()

    def __lookup_geometry(self, rpsuid):
        """
        Finds the geometry of a site.
        :rtype: geometry object
        """
        try:
            rpsuid_sites_f = AddFieldDelimiters(self.sites, "rpsuid")
            with SearchCursor(self.sites, ["SHAPE@", "RPSUID"], where_clause="{0}='{1}'".format(rpsuid_sites_f, rpsuid)) as cur:
                for r in cur:
                    return r[0].projectAs("WGS 1984")
            return False
        except Exception as e:
            self.log.exception(e.message)
            raise Exit()

    def __is_applicable(self, catcode):
        """
        Is CIP or Army CIP Priority 1.
        :rtype: list
        """
        try:
            ccodes_f = AddFieldDelimiters(self.current_use_catcode_table, "RPA_PREDOMINANT_CURRENT_USE_CAT")
            with SearchCursor(self.current_use_catcode_table, ["CIP", "Army_CIP_Priority_1", "Feature_Type"],
                              where_clause="{0}='{1}'".format(ccodes_f, catcode)) as curs:
                for r in curs:
                    if str(r[0]) == '1' or str(r[1]) == '1':
                        return list(r[2].split(', '))
            return False
        except Exception as e:
            self.log.exception(e.message)
            raise Exit()

    def __get_insts_sites(self):
        insts_sites = {}
        with SearchCursor(self.hqiis, ["INSTALLATION_CODE", "SITE_UID"]) as cursor:
            for row in cursor:
                if row[0] not in insts_sites.keys():
                    insts_sites[row[0]] = [row[1]]
                    continue
                if row[1] not in insts_sites[row[0]]:
                    insts_sites[row[0]].append(row[1])
        return insts_sites