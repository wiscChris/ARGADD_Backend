import os
from datetime import datetime

from config.config import Config

config = Config()

today = datetime.now()


class File(object):
    def __init__(self, module, items=()):
        """

        :type module: str
        :type items: list
        """
        self.mod_name = module
        self.items = items
        self.out_folder = config["logs_directory"] + os.sep + "Errors"
        self.file_name = self.out_folder + os.sep + str(today.year) + str(today.month) + str(today.day) + "_" + self.mod_name + "_cache.txt"

    def save(self):
        """

        :rtype: bool
        """
        try:
            with open(self.file_name, 'w+') as out_file:
                out_file.write(str(self.items))
                # csv_out = csv.writer(out_file)
                # c_count = 0
                # out_strings = []
                # out_string = ""
                # for c in str(self.items):
                #     if c_count == 131000:
                #         out_strings.append(out_string)
                #         c_count = 0
                #         out_string = ""
                #     out_string += c
                #     c_count += 1
                # out_strings.append(out_string)
                # csv_out.writerows(out_strings)
            return True
        except:
            return False

    def read(self):
        """

        :rtype: list
        """
        try:
            with open(self.file_name, 'r') as read_file:
                return eval(read_file.readline())
        except IOError:
            return []
