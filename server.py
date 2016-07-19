import os
from BaseHTTPServer import HTTPServer
import ssl
import include.database as database
import include.cache_data as cache_data
import include.timer as timer
from request_handler import HTTPRequestHandlerContainer

__author__ = 'Ameya'


class SemtracServer():
    def __init__(self):
        self.cache = None

    def pre_tasks(self):
        db = database.Database(os.path.abspath(__file__))
        # Cache frequency information
        print "caching frequency information"
        self.cache = cache_data.Cache(db)
        self.cache.cache_frequency_information()

        print "loading n-grams..."
        # with timer.Timer('n-grams load'):
        #     cache.cache_n_grams()

        print "reading dictionary..."
        self.cache.cache_dictionary()

        print "Loading POS Tagger"
        with timer.Timer("Backoff tagger load"):
            pickle_path = "tagging_data/brown_clawstags.pickle"
            coca_tagger_path = "tagging_data/coca_500k.csv"
            self.cache.load_pos_tagger(pickle_path, coca_tagger_path)

    def start_server(self):
        server_address = ('127.0.0.1', 443)
        HTTPHandlerClass = HTTPRequestHandlerContainer(self.cache)
        httpd = HTTPServer(server_address, HTTPHandlerClass)
        httpd.socket = ssl.wrap_socket(httpd.socket, certfile='C:\server.crt', server_side=True, keyfile='C:\server.key')
        print('https server is running...')
        httpd.serve_forever()

if __name__ == '__main__':
    server = SemtracServer()
    server.pre_tasks()
    server.start_server()