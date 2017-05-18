import logging
import os
from xml.dom.minidom import parse
from xml.etree import ElementTree

from arcpy import Exists

from Lib.Exceptions import *

config_file = os.path.split(__file__)[0] + str(r"\config.xml")

class Config(object):
    def __init__(self):
        self.config_file = config_file
        self.config = parse(self.config_file)

    def __getitem__(self, item):
        try:
            return str(self.config.getElementsByTagName(item)[0].firstChild.nodeValue)
        except:
            return None

    def __setitem__(self, key, value):
        try:
            with open(self.config_file, 'w') as f:
                if self.config.getElementsByTagName(key)[0].firstChild.nodeType == \
                        self.config.getElementsByTagName(key)[0].firstChild.TEXT_NODE:
                    self.config.getElementsByTagName(key)[0].firstChild.replaceWholeText(value)
                    f.write(self.config.toxml())
                else:
                    raise Exception
            return True
        except:
            return False


class CheckConfig(object):
    def __init__(self):
        # TODO does not check server params because they might not arcpy.Exists()
        self.parameters = {}
        # Don't touch these!! Referenced in Complete()
        self.param_groups = ["dashboard_layers", "databases", "tool"]
        self.et = ElementTree.parse(config_file)
        for pg in self.param_groups:
            for element in self.et.findall('./{0}/'.format(pg)):
                if not list(element):
                    if pg not in self.parameters.keys():
                        self.parameters[pg] = [element.tag]
                    else:
                        self.parameters[pg].append(element.tag)
        self.logs = self.log()
        self.test_config = Config()

    def complete(self):
        try:
            for dict_item in self.parameters:
                for item in self.parameters[dict_item]:
                    if isinstance(item, str):
                        if dict_item == self.param_groups[1]:
                            if not Exists(self.test_config[item]):
                                raise InaccessibleData("'{0}' does not exist or is inaccessible.".format(item))
                        elif dict_item == self.param_groups[0]:
                            if not Exists(self.test_config['dashboard_database'] + os.sep + self.test_config[item]):
                                raise InaccessibleData("'{0}' does not exist or is inaccessible.".format(item))
                    else:
                        raise ConfigFileIssue("There is an issue with the config file. ({0})".format(item))
            return True
        except (InaccessibleData, ConfigFileIssue) as e:
            self.logs.error(e.message)
            raise Exit()

    @staticmethod
    def log():
        from Lib.ToolLogging import critical_info
        critical_info()
        error_logging = logging.getLogger('ARGADD_errors.main.config.CheckConfig')
        return error_logging
