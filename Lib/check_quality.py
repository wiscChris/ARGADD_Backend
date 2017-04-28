import logging
import Lib.pathos.multiprocessing as mp

from arcpy import ListDatasets, ListFeatureClasses, ListFields, Describe, DomainToTable_management, \
    AddFieldDelimiters, env, MakeTableView_management, Exists
from arcpy.da import SearchCursor, UpdateCursor, Editor, InsertCursor

import tool_logging
from config.config import Config
from Exceptions import *

config = Config()


def log():
    tool_logging.critical_info()
    error_logging = logging.getLogger('ARGADD_errors.main.check_quality')
    return error_logging


log = log()


class Fields(object):
    def __init__(self, db_location):
        self.__cip_table = '\\'.join([db_location, config["qap_fields_cip"]])
        self.__common_table = '\\'.join([db_location, config["qap_fields_common"]])
        self.common_fields = []
        with SearchCursor(self.__common_table, "Name") as c:
            for r in c:
                self.common_fields.append(r[0])

    def __getitem__(self, item):
        fields = self.common_fields
        fc_delim = AddFieldDelimiters(self.__cip_table, "Feature_Class")
        with SearchCursor(self.__cip_table, ["Name_3_1", "Feature_Class"],
                          where_clause="{0}='{1}'".format(fc_delim, item)) as c:
            for r in c:
                if r[0] not in fields:
                    fields.append(r[0])
        return fields


class FieldAnalysis(object):
    def __init__(self, in_db):
        """

        :type in_db: str
        :param in_db: arcgis geodatabase
        """
        try:
            env.overwriteOutput = True
            self.in_db = in_db
            if not Exists(self.in_db):
                raise InaccessibleData("The input data is inaccessible.")
            self.db = config["dashboard_database"]
            self.out_table = '\\'.join([self.db, config["field_quality"]])
            if Exists(self.out_table):
                self.checker()
            else:
                raise InaccessibleData(
                    "There is a bad file path to the dashboard database.\nField quality check did not run.")
        except InaccessibleData as e:
            log.exception(e.message)
            raise
        self.__attributes = []
        self.fc = ''
        self.__all_fields = Fields(self.db)

    def __installation_field_check(self, installation):
        fc = self.fc
        __all_fields = self.__all_fields
        installation_f = AddFieldDelimiters(fc, "installationID")
        MakeTableView_management(fc, "inst_q_table", "{0}='{1}'".format(installation_f, installation))
        querry_table = "inst_q_table"
        qap_fields = __all_fields[fc]
        total = 0
        good = {}
        qap_reqd = {}
        domain_codes = {}
        domain_descs = {}
        fields = ListFields(fc)
        str_fields = []
        for field in fields:
            if field.domain != "":
                domain_table = self.__get_domain_codes(field.domain)
                domain_codes.update({field.name: []})
                domain_descs.update({field.name: []})
                if domain_table:
                    with SearchCursor(domain_table, ["code", "desc"]) as cursor:
                        for row in cursor:
                            domain_codes[field.name].append(row[0])
                            domain_descs[field.name].append(row[1])
        for field in fields:
            good.update({field.name: 0})
            if field.name in qap_fields:
                qap_reqd.update({field.name: "Yes"})
            else:
                qap_reqd.update({field.name: "No"})
            str_fields.append(field.name)

        with SearchCursor(querry_table, str_fields) as cursor:
            for row in cursor:
                total += 1
                index = 0
                while index < len(fields):
                    if fields[index].domain != "":
                        if row[index] in domain_codes[fields[index].name] or row[index] in domain_descs[fields[index].name]:
                            good[fields[index].name] += 1
                    else:
                        if row[index]:
                            good[fields[index].name] += 1
                    index += 1

        if total != 0:
            for field in fields:
                self.__attributes.append([fc,
                                          field.name,
                                          float(float(good[field.name]) / float(total)) * 100,
                                          field.domain,
                                          qap_reqd[field.name],
                                          str(installation)
                                          ])

    def checker(self):
        # type: () -> bool
        try:
            env.workspace = self.in_db
            for dataset in ListDatasets():
                for fc in ListFeatureClasses(feature_dataset=dataset):
                    self.fc = fc
                    p = mp.ProcessingPool()
                    p.map(self.__installation_field_check, self.__get_installations(fc))
                    # for installation in self.__get_installations(fc):
                    #     self.__installation_field_check(installation)

        except Exception as e:
            log.exception(e.message)
            raise
        else:
            self.__write_result_to_table(self.__attributes)
            return True

    def __write_result_to_table(self, list_of_attributes):
        """

        :rtype: bool
        :type list_of_attributes: list of lists of attributes
        """
        layer_f = AddFieldDelimiters(self.out_table, "Layer")
        field_name_f = AddFieldDelimiters(self.out_table, "Field_Name")
        inst_f = AddFieldDelimiters(self.out_table, "installationID")
        with Editor(self.db) as edit:
            try:
                for attributes in list_of_attributes:
                    with UpdateCursor(self.out_table,
                                      ["Layer", "Field_Name", "Quality", "Domain_Name", "QAP_Required",
                                       "installationID"],
                                      where_clause="{0}='{1}' AND {2}='{3}' AND {4}='{5}'".format(layer_f,
                                                                                                  attributes[0],
                                                                                                  field_name_f,
                                                                                                  attributes[1],
                                                                                                  inst_f,
                                                                                                  attributes[5])) as cursor:
                        for _ in cursor:
                            row = attributes
                            cursor.updateRow(row)
                        else:
                            with InsertCursor(self.out_table,
                                              ["Layer", "Field_Name", "Quality", "Domain_Name", "QAP_Required",
                                               "installationID"]) as c:
                                c.insertRow(attributes)
                return True
            except Exception as e:
                log.exception(e)
                raise

    @staticmethod
    def __get_installations(table):
        """

        :type table: arcpy table view
        :rtype: list of installations ids
        """
        installation_ids = []
        with SearchCursor(table, ["installationID"]) as cursor:
            for row in cursor:
                installation_ids.append(row[0])
        return installation_ids

    def __get_domain_codes(self, domain_name):
        env.workspace = self.in_db
        db_described = Describe(self.in_db)
        if domain_name in db_described.domains:
            domain_table = DomainToTable_management(self.in_db, domain_name, r"in_memory\domain", "code", "desc")
            return domain_table
        else:
            return False

# def execute(params):
#     try:
#         FieldAnalysis(params[0].valueAsText)
#     except:
#         pass
