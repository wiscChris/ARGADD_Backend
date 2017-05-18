import logging
import os

from arcpy import AddFieldDelimiters
from arcpy.da import UpdateCursor, InsertCursor, Editor

from Cache import File
from Exceptions import *
from ToolLogging import critical_info


def log():
    critical_info()
    error_logging = logging.getLogger('ARGADD_errors.CheckForNeeds.LayerStatus')
    return error_logging


class LayerStatus:
    def __init__(self, out_table):
        self.__layers = self.__read_cache()
        self.table = out_table
        self.log = log()

    def add_status(self, installation, site, feature_type, status):
        """
        status types: 0 - does not exist at installation
                      1 - exists both in HQIIS and in GIS data
                      2 - exists in HQIIS but not in GIS data
        :rtype: bool
        :type status: int
        """
        try:
            # Cannot change a 2 status to 1
            if self.__layers[installation][site][feature_type] == 2 and status == 1:
                return True
            else:
                self.__layers[installation][site][feature_type] = status
        except KeyError:
            try:
                self.__layers[installation][site] = {feature_type: status}
            except KeyError:
                self.__layers[installation] = {site: {feature_type: status}}

    def post_to_table(self):
        table_fields = ["Installation", "rpsuid", "Feature_Type", "Status"]
        inst_f = AddFieldDelimiters(self.table, table_fields[0])
        site_f = AddFieldDelimiters(self.table, table_fields[1])
        ft_f = AddFieldDelimiters(self.table, table_fields[2])
        try:
            with Editor(os.path.split(self.table)[0]) as _:
                for inst in self.__layers:
                    for site in self.__layers[inst]:
                        for layer in self.__layers[inst][site]:
                            status = self.__layers[inst][site][layer]
                            with UpdateCursor(self.table, table_fields[3], where_clause="{0}='{1}' AND {2}='{3}' AND {4}='{5}'".format(
                                    inst_f, str(inst), site_f, str(site), ft_f, layer)) as cursor:
                                row_count = 0
                                for row in cursor:
                                    row[0] = str(status)
                                    cursor.updateRow(row)
                                    row_count += 1
                                if not row_count:
                                    with InsertCursor(self.table, table_fields) as insert:
                                        insert.insertRow([str(inst), str(site), layer, str(status)])
            return True
        except Exception as e:
            self.log.exception(e.message)
            raise Exit("Failed from LayerStatus.post_to_table")

    def baseline_the_table(self, insts_sites, feature_types):
        """

        :rtype: bool
        :type feature_types: list
        :type insts_sites: dict
        """
        if not self.__layers == {}:
            return True
        table_fields = ["Installation", "rpsuid", "Feature_Type", "Status"]
        inst_f = AddFieldDelimiters(self.table, table_fields[0])
        site_f = AddFieldDelimiters(self.table, table_fields[1])
        ft_f = AddFieldDelimiters(self.table, table_fields[2])
        try:
            with Editor(os.path.split(self.table)[0]) as _:
                for inst in insts_sites:
                    for site in insts_sites[inst]:
                        for layer in feature_types:
                            try:
                                if self.__layers[inst][site][layer]:
                                    continue
                            except KeyError:
                                self.add_status(inst, site, layer, 0)
                            ## Code deemed too  slow
                            # with UpdateCursor(self.table, table_fields[3],
                            #                   where_clause="{0}='{1}' AND {2}='{3}' AND {4}='{5}'".format(
                            #                           inst_f, str(inst), site_f, str(site), ft_f, layer)) as cursor:
                            #     row_count = 0
                            #     for row in cursor:
                            #         row[0] = str(0)
                            #         cursor.updateRow(row)
                            #         row_count += 1
                            #     if not row_count:
                            #         with InsertCursor(self.table, table_fields) as insert:
                            #             insert.insertRow([str(inst), str(site), layer, str(0)])
            return True
        except Exception as e:
            self.log.exception(e.message)
            raise Exit("Failed from LayerStatus.baseline_the_table")

    def write_cache(self):
        """

        :rtype: bool
        """
        cache = File("LayerStatus", [self.__layers])
        cache.save()
        return True

    def __read_cache(self):
        """

        :rtype: dict
        """
        cache = File("LayerStatus")
        out = cache.read()
        if out:
            return out[0]
        return {}
