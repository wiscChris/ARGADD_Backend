import logging

from arcpy import ListDatasets, ListFeatureClasses, ListFields, Describe, DomainToTable_management, \
    AddFieldDelimiters, env, MakeTableView_management
from arcpy.da import SearchCursor, UpdateCursor, Editor, InsertCursor

from Exceptions import *
from ToolLogging import critical_info
from config.config import Config

config = Config()

def log():
    critical_info()
    error_logging = logging.getLogger('ARGADD_errors.main.CheckFieldQuality')
    return error_logging


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
            self.log = log()
            env.overwriteOutput = True
            self.in_db = in_db
            self.db = config["dashboard_database"]
            self.__attributes = []
            self.__fc = ''
            self.__all_fields = Fields(self.db)
            self.out_table = '\\'.join([self.db, config["field_quality"]])
        except InaccessibleData as e:
            self.log.exception(e.message)
            raise Exit()

    def checker(self):
        # type: () -> bool
        try:
            env.workspace = self.in_db
            for dataset in ListDatasets():
                for fc in ListFeatureClasses(feature_dataset=dataset):
                    self.__fc = fc
                    self.__fc_fields = ListFields(self.__fc)
                    for installation in self.__get_installations(fc):
                        if installation:
                            self.__installation_field_check(installation)

        except Exception as e:
            self.log.exception(e.message)
            raise Exit()
        else:
            self.__write_result_to_table(self.__attributes)
            return True

    def __installation_field_check(self, installation):
        installation_f = AddFieldDelimiters(self.__fc, "installationID")
        if installation == 'ALL':
            sql_inst_where = None
        else:
            sql_inst_where = "{0}='{1}'".format(installation_f, installation)
        MakeTableView_management(self.__fc, "inst_q_table", sql_inst_where)
        querry_table = "inst_q_table"
        qap_fields = self.__all_fields[self.__fc]
        total = 0
        good = {}
        qap_reqd = {}
        domain_codes = {}
        domain_descs = {}
        str_fields = []
        for field in self.__fc_fields:
            if field.domain != "":
                domain_table = self.__get_domain_codes(field.domain)
                domain_codes.update({field.name: []})
                domain_descs.update({field.name: []})
                if domain_table:
                    with SearchCursor(domain_table, ["code", "desc"]) as cursor:
                        for row in cursor:
                            domain_codes[field.name].append(row[0])
                            domain_descs[field.name].append(row[1])
        for field in self.__fc_fields:
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
                while index < len(self.__fc_fields):
                    if self.__fc_fields[index].domain != "":
                        if row[index] in domain_codes[self.__fc_fields[index].name] or row[index] in domain_descs[self.__fc_fields[index].name]:
                            good[self.__fc_fields[index].name] += 1
                    else:
                        if row[index]:
                            good[self.__fc_fields[index].name] += 1
                    index += 1

        if total != 0:
            for field in self.__fc_fields:
                self.__attributes.append([self.__fc,
                                          field.name,
                                          float(float(good[field.name]) / float(total)) * 100,
                                          field.domain,
                                          qap_reqd[field.name],
                                          str(installation)
                                          ])

    def __write_result_to_table(self, list_of_attributes):
        """

        :rtype: bool
        :type list_of_attributes: list of lists of attributes
        """
        layer_f = AddFieldDelimiters(self.out_table, "Layer")
        field_name_f = AddFieldDelimiters(self.out_table, "Field_Name")
        inst_f = AddFieldDelimiters(self.out_table, "installationID")
        with Editor(self.db) as _:
            try:
                for attributes in list_of_attributes:
                    with UpdateCursor(self.out_table,
                                      ["Layer", "Field_Name", "Quality", "Domain_Name", "QAP_Required",
                                       "installationID"],
                                      where_clause="{0}='{1}' AND {2}='{3}' AND {4}='{5}'".format(layer_f,
                                                                                                  str(attributes[0]),
                                                                                                  field_name_f,
                                                                                                  str(attributes[1]),
                                                                                                  inst_f,
                                                                                                  str(attributes[5]))) as cursor:
                        for _ in cursor:
                            row = attributes
                            cursor.updateRow(row)
                            break
                        else:
                            with InsertCursor(self.out_table,
                                              ["Layer", "Field_Name", "Quality", "Domain_Name", "QAP_Required",
                                               "installationID"]) as c:
                                c.insertRow(attributes)
                return True
            except Exception as e:
                self.log.exception(e)
                raise Exit()

    def __get_installations(self, table):
        """

        :type table: arcpy table view
        :rtype: list of installations ids
        """
        # TODO all installation ids need to be populated properly...
        installation_ids = []
        if "installationID" not in [n.name for n in self.__fc_fields]:
            installation_ids.append("ALL")
            return installation_ids
        with SearchCursor(table, ["installationID"]) as cursor:
            for row in cursor:
                if row[0] not in installation_ids:
                    installation_ids.append("{0}".format(row[0]))
        return installation_ids

    def __get_domain_codes(self, domain_name):
        env.workspace = self.in_db
        db_described = Describe(self.in_db)
        if domain_name in db_described.domains:
            domain_table = DomainToTable_management(self.in_db, domain_name, r"in_memory\domain", "code", "desc")
            return domain_table
        else:
            return False
