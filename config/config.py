import os
from xml.dom.minidom import parse


class Config(object):
    def __init__(self):
        self.config_file = os.path.split(__file__)[0] + str(r"\config.xml")
        self.config = parse(self.config_file)

    def get(self, param_name):
        """
            :type param_name: str
            :rtype: str
            """
        try:
            return str(self.config.getElementsByTagName(param_name)[0].firstChild.nodeValue)
        except:
            return None

    def set(self, param_name, new_var):
        """
        :type param_name: str
        :param param_name: str
        :param new_var: str
        :return: bool
        """
        try:
            with open(self.config_file, 'w') as f:
                if self.config.getElementsByTagName(param_name)[0].firstChild.nodeType == \
                        self.config.getElementsByTagName(param_name)[0].firstChild.TEXT_NODE:
                    self.config.getElementsByTagName(param_name)[0].firstChild.replaceWholeText(new_var)
                    f.write(self.config.toxml())
                else:
                    raise Exception
            return True
        except:
            return False

