import os
from BaseHTTPServer import HTTPServer
import ssl
import include.db_conn as db_conn
import include.timer as timer

__author__ = 'Ameya'


class SemtracServer():
    class __SemtracServer():
        def __init__(self):
            self.cache = None
            self.db = None

        def get_db_conn(self):
            if self.db is None:
                self.db = db_conn.Database(os.path.abspath(__file__))
            return self.db.get_conn()

        def get_db_cursor(self):
            if self.db is None:
                self.db = db_conn.Database(os.path.abspath(__file__))
            return self.db.get_cursor()

        def pre_tasks(self):
            if self.db is None:
                self.db = db_conn.Database(os.path.abspath(__file__))
            # Cache frequency information
            print "caching frequency information"
            import include.cache_data as cache_data
            self.cache = cache_data.Cache(self.db)
            self.cache.cache_frequency_information()

            print "loading n-grams..."
            with timer.Timer('n-grams load'):
                self.cache.cache_n_grams()

            print "reading dictionary..."
            self.cache.cache_dictionary()

            print "Loading POS Tagger"
            with timer.Timer("Backoff tagger load"):
                pickle_path = "tagging_data/brown_clawstags.pickle"
                coca_tagger_path = "tagging_data/coca_500k.csv"
                self.cache.load_pos_tagger(pickle_path, coca_tagger_path)

        def start_server(self):
            server_address = ('0.0.0.0', 443)
            from request_handler import HTTPRequestHandlerContainer
            HTTPHandlerClass = HTTPRequestHandlerContainer()
            httpd = HTTPServer(server_address, HTTPHandlerClass)
            httpd.socket = ssl.wrap_socket(httpd.socket, certfile='cert/server.crt', server_side=True, keyfile='cert/server.key')
            print('https server is running...')
            httpd.serve_forever()

    __instance = None

    def __init__(self):
        if SemtracServer.__instance is None:
            SemtracServer.__instance = SemtracServer.__SemtracServer()
        self.__dict__['SemtracServer__instance'] = SemtracServer.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)

if __name__ == '__main__':
    server = SemtracServer()
    server.pre_tasks()
    server.start_server()
