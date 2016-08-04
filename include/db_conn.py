import MySQLdb.cursors
import util

__author__ = 'Ameya'


class Database():
    class __Database():
        def __init__(self, root_path):
            credentials = util.dbcredentials(root_path)
            self.connection = MySQLdb.connect(host=credentials["host"],  # your host, usually localhost
                                         user=credentials["user"],  # your username
                                         passwd=credentials["password"],  # your password
                                         db=credentials["db"],
                                         cursorclass=MySQLdb.cursors.SSDictCursor)  # stores result in the server. records as dict

        def get_conn(self):
            return self.connection

        def get_cursor(self):
            return self.connection.cursor()

    __instance = None

    def __init__(self, root_path=None):
        if Database.__instance is None:
            Database.__instance = Database.__Database(root_path)
        self.__dict__['Database__instance'] = Database.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)