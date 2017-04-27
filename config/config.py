import os
from xml.dom.minidom import parse


class Config(object):
    def __init__(self):
        self.config_file = os.path.split(__file__)[0] + str(r"\config.xml")
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
