import logging

from arcpy import ListDatasets, ListFeatureClasses, ListFields, env, Describe, DomainToTable_management, \
    AddFieldDelimiters, env, MakeTableView_management
from arcpy.da import SearchCursor, UpdateCursor, Editor, InsertCursor

import tool_logging
from config.config import Config

config = Config()


def error_log():
    tool_logging.critical_errors()
    error_logging = logging.getLogger('ARGADD_errors.main.check_quality')
    return error_logging


def info_log():
    tool_logging.information()
    info_logging = logging.getLogger('ARGADD_errors.main.check_quality')
    return info_logging


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
        with SearchCursor(self.__cip_table, ["Name_3_1", "Feature_Class"], where_clause="{0}='{1}'".format(fc_delim, item)) as c:
            for r in c:
                if r[0] not in fields:
                    fields.append(r[0])
        return fields


class FieldAnalysis(object):
    def __init__(self, in_db):
        env.overwriteOutput = True
        self.in_db = in_db
        self.db = config["dashboard_database"]
        self.out_table = '\\'.join([self.db, config["field_quality"]])
        self.checker()

    def checker(self):
        env.workspace = self.in_db
        __all_fields = Fields(self.db)
        for dataset in ListDatasets():
            for fc in ListFeatureClasses(feature_dataset=dataset):
                fc_attributes = []
                for installation in self.__get_installations(fc):
                    info_log().info(installation)
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
                        fc_attributes = []
                        for field in fields:
                            fc_attributes.append([fc,
                                                 field.name,
                                                 float(float(good[field.name])/float(total)) * 100,
                                                 field.domain,
                                                 qap_reqd[field.name],
                                                  ])
                self.__write_result_to_table(fc_attributes)

    def __write_result_to_table(self, list_of_attributes):
        layer_f = AddFieldDelimiters(self.out_table, "Layer")
        field_name_f = AddFieldDelimiters(self.out_table, "Field_Name")
        with Editor(self.db) as edit:
            try:
                for attributes in list_of_attributes:
                    with UpdateCursor(self.out_table,
                                      ["Layer", "Field_Name", "Quality", "Domain_Name", "QAP_Required", "installationID"],
                                      where_clause="{0}='{1}' AND {2}='{3}'".format(layer_f, attributes[0], field_name_f, attributes[1])) as cursor:
                        for row in cursor:
                            row = attributes
                            cursor.updateRow(row)
                        else:
                            with InsertCursor(self.out_table, ["Layer", "Field_Name", "Quality", "Domain_Name", "QAP_Required", "installationID"]) as c:
                                c.insertRow(attributes)
            except Exception as e:
                error_log().exception(e)

    def __get_installations(self, table):
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
