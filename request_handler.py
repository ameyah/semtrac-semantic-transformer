from BaseHTTPServer import BaseHTTPRequestHandler
from controllers import Controllers

__author__ = 'Ameya'


def HTTPRequestHandlerContainer(cache_obj):
    global db, options, participantObj

    class HTTPRequestHandler(BaseHTTPRequestHandler):

        def __init__(self, request, client_address, server):
            BaseHTTPRequestHandler.__init__(self, request, client_address, server)
            self.controller = Controllers()

        # handle POST command
        def do_POST(self):
            print self.path
            if "/prestudy/answers" in self.path:
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                postvars = self.get_post_data(ctype, pdict)
                if postvars != '':
                    answers = json.loads(postvars['answers'][0])
                    result = insert_prestudy_answers(db, participantObj.get_participant_id(), answers)
                    self.send_ok_response(data=result)
                else:
                    self.send_bad_request_response()

            elif "/poststudy/answers" in self.path:
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                postvars = self.get_post_data(ctype, pdict)
                if postvars != '':
                    answers = json.loads(postvars['answers'][0])
                    result = insert_poststudy_answers(db, participantObj.get_participant_id(), answers)
                    self.send_ok_response(data=result)
                else:
                    self.send_bad_request_response()

            elif "/website/save" in self.path:
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                postvars = self.get_post_data(ctype, pdict)
                if postvars != '':
                    websiteListData = json.loads(postvars['data'][0])

                    # save website list
                    insert_website_list(db, participantObj.get_participant_id(), websiteListData)
                    # website_list_info = get_website_list_probability(db, websiteListData)
                    self.send_ok_response()
                else:
                    self.send_bad_request_response()

            elif "/participant/id" in self.path:
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                postvars = self.get_post_data(ctype, pdict)
                # set current active participant
                if postvars != '':
                    # Clear password hashes just to make sure we are clear
                    clear_password_key(db)
                    words_mapping.clear_word_mapping()
                    participantObj.set_participant_id(int(postvars['id'][0]))
                    self.send_ok_response()
                else:
                    self.send_bad_request_response()

            elif "/participant/website/add" in self.path:
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                postvars = self.get_post_data(ctype, pdict)
                if postvars != '':
                    website_url = str(postvars['url'][0])
                    website_importance = int(postvars['importance'][0])
                    result = add_new_website(db, participantObj.get_participant_id(), website_url, website_importance)
                    self.send_ok_response(data=result)
                else:
                    self.send_bad_request_response()

            elif "/participant/website" in self.path:
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                postvars = self.get_post_data(ctype, pdict)
                # set current active participant
                if postvars != '':
                    participantObj.set_active_website(str(postvars['url'][0]))
                    self.send_ok_response()
                else:
                    self.send_bad_request_response()

            else:
                self.send_bad_request_response()

        def get_post_data(self, ctype, pdict):
            if ctype == 'multipart/form-data':
                postvars = cgi.parse_multipart(self.rfile, pdict)
            elif ctype == 'application/x-www-form-urlencoded':
                length = int(self.headers.getheader('content-length'))
                postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
            else:
                postvars = ''
            return postvars

        # handle GET command
        def do_GET(self):
            try:
                if "/online" in self.path:
                    self.send_ok_response(data=1)

                elif "/participant/id" in self.path:
                    parsed = urlparse.urlparse(self.path)
                    one_way_hash = urlparse.parse_qs(parsed.query)['hash'][0]
                    self.controller.new_participant_record(one_way_hash)

                    self.send_ok_response(data=participant_id)

                elif "/study/questions" in self.path:
                    parsed = urlparse.urlparse(self.path)
                    question_type = urlparse.parse_qs(parsed.query)['type'][0]
                    result = get_study_questions(db, participantObj.get_participant_id(), question_type)
                    self.send_ok_response(data=json.dumps(result))

                elif "/transform" in self.path:
                    # getParams = self.path.split("transform?")[1]
                    parsed = urlparse.urlparse(self.path)
                    clearPassword = urlparse.parse_qs(parsed.query)['pass'][0]
                    try:
                        clearUsername = urlparse.parse_qs(parsed.query)['user'][0]
                    except KeyError:
                        # Username not captured
                        # use previous username
                        clearUsername = participantObj.get_previous_username()
                    try:
                        passwordStrength = urlparse.parse_qs(parsed.query)['strength'][0]
                    except KeyError:
                        passwordStrength = 0
                    try:
                        passwordWarning = urlparse.parse_qs(parsed.query)['warning'][0]
                    except KeyError:
                        passwordWarning = ""

                    # For websiteUrl, first check whether participantObj has an active url
                    activeWebsite = participantObj.get_active_website()
                    if activeWebsite != '':
                        websiteUrl = activeWebsite
                    else:
                        # get active page URL from GET params
                        websiteUrl = urlparse.parse_qs(parsed.query)['url'][0]
                        previousActiveWebsite = participantObj.get_previous_active_website()
                        if checkWebsiteSyntacticSimilarity(websiteUrl, previousActiveWebsite):
                            websiteUrl = previousActiveWebsite
                    clearPasswordURIDecoded = urllib.unquote(urllib.unquote(clearPassword))
                    clearUsernameURIDecoded = urllib.unquote(urllib.unquote(clearUsername))
                    self.send_ok_response()

                    # First insert the login website in the database
                    transformed_cred_id = get_transformed_credentials_id(db, participantObj.get_participant_id(),
                                                                         websiteUrl, passwordStrength, passwordWarning)
                    participantObj.set_transformed_cred_id(transformed_cred_id)

                    self.segmentPassword(clearPasswordURIDecoded, True)
                    self.posTagging()
                    self.grammarGeneration(transformed_cred_id, clearPassword=clearPasswordURIDecoded)

                    # Delete original password after transformation
                    self.clearOriginalData()

                    # Transform usernames semantically. We'll use the same functions for now.
                    # as the procedure is same, except that we dont have to store grammar.
                    # First check if username is email, if it is then extract email username and transform only the
                    # username
                    email_split_flag = False
                    if re.match("[^@]+@[^@]+\.[^@]+", clearUsernameURIDecoded):
                        email_username = clearUsernameURIDecoded.split("@")[0]
                        email_split_flag = True
                    else:
                        email_username = clearUsernameURIDecoded
                    self.segmentPassword(email_username, False)
                    self.posTagging()
                    self.grammarGeneration(transformed_cred_id, type="username")

                    if email_split_flag:
                        # Now append the email domain to the transformed Username
                        email_domain = "@" + clearUsernameURIDecoded.split("@")[1]
                        append_email_domain(db, transformed_cred_id, email_domain)

                    # store clearUsername in participantObj
                    participantObj.set_active_username(clearUsernameURIDecoded)
                    self.clearOriginalData()

                    participantObj.reset_active_website()
                elif "/participant/results" in self.path:
                    parsed = urlparse.urlparse(self.path)
                    one_way_hash = urlparse.parse_qs(parsed.query)['hash'][0]
                    # First clear the password hashes
                    clear_password_key(db)
                    words_mapping.clear_word_mapping()
                    resultDict = get_transformed_passwords_results(db, one_way_hash)
                    self.send_ok_response(data=json.dumps(resultDict))
                elif "/website/importance" in self.path:
                    parsed = urlparse.urlparse(self.path)
                    website_url = urlparse.parse_qs(parsed.query)['url'][0]
                    if website_url != '':
                        importance = get_website_probability(db, website_url)
                        print website_url + " - " + importance
                        self.send_ok_response(data=importance)
                    else:
                        self.send_bad_request_response()
                elif "/website/list/importance" in self.path:
                    parsed = urlparse.urlparse(self.path)
                    # print json.loads(urlparse.parse_qs(parsed.query)['urls'][0])
                    website_urls = json.loads(urlparse.parse_qs(parsed.query)['urls'][0])
                    website_importance_data = get_website_list_probability(db, website_urls)
                    self.send_ok_response(data=json.dumps(website_importance_data))
                    """
                    if website_url != '':
                        importance = get_website_probability(db, website_url)
                        print website_url + " - " + importance
                        self.send_ok_response(data=importance)
                    else:
                        self.send_bad_request_response()

                    """
                elif "/auth" in self.path:
                    parsed = urlparse.urlparse(self.path)
                    auth_status = urlparse.parse_qs(parsed.query)['success'][0]
                    transformed_cred_id = participantObj.get_transformed_cred_id()
                    save_auth_status(db, transformed_cred_id, auth_status)
                    self.send_ok_response()
                else:
                    self.send_bad_request_response()
            except oursql.Error as e:
                print e
                print "exception"
                clearPassword = ''

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

        def segmentPassword(self, clearPassword, checkSpecialChars):
            wbuff = WriteBuffer(db, dictionary, 100000)

            if len(clearPassword) == 0:
                return
            if clearPassword.strip(" ") == '':
                return

            # add Password to database temporarily.
            pass_id = addSocketPassword(db, clearPassword, participantObj.get_participant_id())

            res = mineLine(db, clearPassword, dictionary, freqInfo, checkSpecialChars)
            if options.verbose:
                print "[Done]"

            # store results
            if len(res) > 0:
                flush = wbuff.addCommit(pass_id, res)

            wbuff._flush()  # flush the rest

        def posTagging(self):
            try:
                self.passwordSegmentsDb = database.PwdDb(participantObj.get_participant_id(), sample=options.sample,
                                                         save_cachesize=500000)
                pos_tagger.main(self.passwordSegmentsDb, pos_tagger_data, options.dryrun, options.stats,
                                options.verbose)
            except:
                e = sys.exc_info()[0]
                traceback.print_exc()
                sys.exit(1)

        def grammarGeneration(self, transformed_password_id, **kwargs):
            # grammar.select_treecut(options.password_set, 5000)
            self.passwordSegmentsDb = database.PwdDb(participantObj.get_participant_id(), sample=options.sample)
            try:
                grammar.main(self.passwordSegmentsDb, transformed_password_id, participantObj.get_participant_id(),
                             options.dryrun,
                             options.verbose,
                             "../grammar3", options.tags, type=kwargs.get("type"),
                             clearPassword=kwargs.get("clearPassword"))
            except KeyboardInterrupt:
                db.finish()
                raise


        def clearOriginalData(self):
            clear_original_data(db)


    return HTTPRequestHandler
