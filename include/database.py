import MySQLdb.cursors
import util

__author__ = 'Ameya'


class Database():
    def __init__(self, root_path):
        credentials = util.dbcredentials(root_path)
        self.connection = MySQLdb.connect(host=credentials["host"],  # your host, usually localhost
                                     user=credentials["user"],  # your username
                                     passwd=credentials["password"],  # your password
                                     db=credentials["db"],
                                     cursorclass=MySQLdb.cursors.SSDictCursor)  # stores result in the server. records as dict

    def get_cursor(self):
        return self.connection.cursor()