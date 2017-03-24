from BaseHTTPServer import BaseHTTPRequestHandler
import json
from controllers import Controllers
import include.util as utils
import MySQLdb

__author__ = 'Ameya'


def HTTPRequestHandlerContainer():

    controller = Controllers()

    class HTTPRequestHandler(BaseHTTPRequestHandler):

        def __init__(self, request, client_address, server):
            BaseHTTPRequestHandler.__init__(self, request, client_address, server)
            # self.controller = Controllers()

        # handle POST command
        def do_POST(self):
            print self.path
            self.send_ok_response()

        # handle GET command
        def do_GET(self):
            try:
                if "/transform" in self.path:
                    clear_password = utils.get_get_param(self.path, 'pass')
                    self.send_ok_response()
                    segment_pos = controller.transform_credentials(clear_password)
                    segment_pos = json.dumps(segment_pos)
                    self.send_ok_response(data=segment_pos)
                else:
                    self.send_bad_request_response()
            except MySQLdb.Error as e:
                print e
                print "exception"
                clear_password = ''
                controller.clear_plain_text_data()

            return

        def send_ok_response(self, **kwargs):
            # send code 200 response
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            if kwargs.get("data"):
                self.wfile.write(kwargs.get("data"))

        def send_bad_request_response(self):
            # send code 200 response
            self.send_response(400)
            self.send_header('Access-Control-Allow-Origin', '*')

        # suppress logs
        def log_message(self, format, *args):
            return

    return HTTPRequestHandler
