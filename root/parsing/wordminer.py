#!/usr/bin/env python
import cgi
import traceback
import urlparse

if __name__ == '__main__' and __package__ is None:
    import os
    from os import sys

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from argparse import ArgumentParser
from custom_exceptions import AllowedTimeExceededError
from cache import *
from queries import *
from utils import *
import argparse
import os
import oursql
import re
import time
import timer
import util
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import ssl
import urllib
import json
import participant
import hashlib

# Import POS Tagger
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pos_tagger
import database
import grammar


# the ids should be in priority order
# names (20, 30, 40) take precedence over cities (60) and countries (50) 
dict_sets = [10, 20, 30, 40, 60, 50, 80, 90]
# sys.argv = ['testWordMiner.py', '-d', [10, 60, 50, 20, 30, 40, 80, 90], '-p', '1']

ENABLE_CHAR_CHUNKS = True


# database Authentication Parameters
# USER = ""
# PASSWORD = ""


def fileLength(fname, fcode='utf-8'):
    '''Finds the line count of a file using a loop.'''
    lines = 0
    with open(fname, encoding=fcode, mode='r') as f:
        for line in f:
            lines += 1
    return lines


def connectToDb():
    '''Contains the connection string to the database, and returns the connection object.'''
    cred = util.dbcredentials()
    return oursql.connect(host=cred["host"], user=cred["user"], passwd=cred["password"], db='passwords',
                          raise_on_warnings=False, charset='utf8', use_unicode=True, port=int(cred["port"]))
    # return oursql.connect(unix_socket='/var/lib/mysql/mysql.sock', user='root',
    # passwd='vialab', db='newtest', charset='utf8', use_unicode=True)


def makeSearchingDict(words):
    '''Takes an iterable words, iterates over it, dumping it into a dict of {word.lower():word,...}'''
    temp = dict()
    for line in words:
        temp[line.strip().lower()] = line.strip()
    return temp


def permuteString(word):
    '''Takes a string, outputs a list of permutations of lengths in a list.
    
    Used by the miner to get strings it can look up in the hash tree
    (aka, python dict), as a speed improvement.
    '''
    wordperm = list()
    for size in range(1, len(word) + 1):
        for pos in range(0, len(word) - size + 1):
            wordperm.append((word[pos:pos + size], pos, pos + size))
    return wordperm


def checkResSubstr(results):
    '''Checks the results for substrings.
    
    This is good for speed, and bad if you actually like correct results.
    '''
    good = set()
    substr = False
    for y in range(0, len(results)):
        for x in reversed(range(y + 1, len(results))):
            if results[y][0].lower() in results[x][0].lower():
                substr = True
                break
        if substr is False:
            good.add(results[y])
        substr = False
    return list(good)


def orderSortSubsList(subslist):
    '''Expects a list of tuples conforming to (word, s_index, e_index)
    
    Sorts the list according to an order believed to produce the faster running
    of the algorithm.
    '''
    # sorts first by e_index, then sorts by s_index
    temp = sorted(subslist, key=lambda x: x[2], reverse=False)
    return sorted(temp, key=lambda x: x[1])


def evalLen(wordList):
    '''Evaluates the total length of a list of words put in, in the standard processing format of this program.'''
    totlen = 0
    for word in wordList:
        totlen += word[2] - word[1]
    return totlen


def retWordLists(x, currWord, remWords):
    '''Somehow returns a weird list/copy of the words list. don't know why i made it exactly.'''
    tempCW = list()
    tempRW = list()
    for v in currWord:
        tempCW.append(v)
    for v in remWords:
        tempRW.append(v)
    tempCW.append(x)
    tempRW.remove(x)
    tempRW = possibleTailStrings(tempCW[-1], tempRW)
    return (tempCW, tempRW)


# tie-breaking based on frequency of word (tries to find the candidate
# with the least odd word).
def getFreqBasedWinner(db, candidatesList):
    listOfFreq = []
    minF = []
    k = 0

    if (len(candidatesList) > 1):
        for x in candidatesList:
            for xword in x[0][0]:
                f = getFreq(db, xword[0])
                listOfFreq.append(f)
            minF.append((k, min(listOfFreq)))
            k = k + 1
            listOfFreq = []
        maxF = max_freq(minF)
        bestList = candidatesList[maxF[0]]
    elif (len(candidatesList) == 1):
        bestList = candidatesList[0]

    return bestList


def getResultWithFewestWords(candidateList):
    bestList = [candidateList[0]]

    for x in candidateList[1:]:
        if (len(x[0][0]) > len(bestList[0][0][0])):
            continue
        elif (len(x[0][0]) < len(bestList[0][0][0])):
            bestList = [x]
        else:
            bestList.append(x)

    return bestList


# Returns probability score based on frequencies of existing bigrams/trigrams.
# frequency info will be set by the calling function getWinningBigramTrigram...
def getBestBigramTrigramScore_r(db, x, numWords, freqInfo, dictionary):
    tempf = 0
    score = 0
    result = 0

    # Base cases: the word frequency is found in unigram, bigram, or trigram lists
    if (numWords == 1):
        tempf = getFreq(db, x[0][0])
        # if word is not in COCA but it's in other dictionary set magic frequency value
        if tempf == 0 and x[0][0] in dictionary:
            tempf = 1
        setSize = freqInfo[0]

    elif (numWords == 2):
        tempf = getBigramFreq(db, x[0][0], x[1][0])
        setSize = freqInfo[1]

    elif (numWords == 3):
        tempf = getTrigramFreq(db, x[0][0], x[1][0], x[2][0])
        setSize = freqInfo[2]

    if (tempf > 0):
        result = numWords
        score = float(tempf) / float(setSize)

    # # Debugging
    # for i in range(0, numWords):
    # print x[i][0], ' ',
    # print tempf, ' ', result, ' ', score

    # Recursive case: the word frequency was not found, and we have at least
    # one word to try out.
    if (score == 0 and numWords >= 1):
        i = 1
        while (i <= 3):
            scorei = float(0)
            resulti = 0
            tmpscore = float(0)
            tmpres = 0

            if (numWords > i):
                (scorei, resulti) = getBestBigramTrigramScore_r(db, x[0:i], i, freqInfo, dictionary)
                (tmpscore, tmpres) = getBestBigramTrigramScore_r(db, x[i:numWords], numWords - i, freqInfo, dictionary)

                # calculate the combined probability scores.
                scorei = scorei * tmpscore
                resulti = resulti + tmpres

            # only update the score if this combination turned out to be better.
            if (scorei > score):
                (score, result) = (scorei, resulti)
            i = i + 1

            # the result portion of this return value may not be necessary.
    return (score, result)


def getBigramTrigramBasedWinner(db, candidateList, freqInfo, dictionary):
    bestList = []
    if (len(candidateList) == 1):
        bestList = candidateList
    else:
        highestScore = 0.0
        # db = connectToDb()
        score = float(0)

        for x in candidateList:
            numWords = len(x[0][0])
            # note that score represents best frequency score by bigrams and trigrams
            (score, result) = getBestBigramTrigramScore_r(db, x[0][0], numWords, freqInfo, dictionary)

            # print x, ' ', score, '\n'

            if (score > highestScore):
                highestScore = score
                bestList = [x]
            elif (score == highestScore):
                bestList.append(x)

        if (len(bestList) == 0):
            bestList = candidateList
    return bestList


def bestCandidate(db, password, candidates, freqInfo, dictionary):
    ''' Receives a list of candidate segmentations and selects the best
        based on the following criteria:
        1. Coverage
        2. Recursive n-gram scoring - product of frequencies of n-grams (trigram/bigram/unigram) 
        3. Oddest single word - frequency of the least frequent word
    '''

    if len(candidates) is 0:
        return candidates

    temp = list()
    maxCoverage = 0

    # First metric to select best result is coverage -- compile a list of the sets
    # that provide the best word-coverage.
    for x in candidates:
        if x[1] < maxCoverage:
            # the coverage of this one is shorter than what we already have.
            continue
        elif x[1] == maxCoverage:
            # it's the same maxCoverage
            temp.append(x)
        elif x[1] > maxCoverage:
            maxCoverage = x[1]
            # doesn't matter how many words we have, replace.
            temp = list()
            temp.append(x)

    # Next we overwrite candidates, reformatting the entries (so all wordList are in a consistent format)
    candidates = []
    for t in temp:
        for x in t[0]:
            """ Note: we're putting x in an array to maintain compatibility
            with database writing functions."""
            candidates.append(([x], t[1]))

    # Run the core tie-breaker. Try to get the best result based on
    # whether it exists in bigram/trigram lists.
    maxCovList = getBigramTrigramBasedWinner(db, candidates, freqInfo, dictionary)

    # finally, if we still have a tie, try to get the winning
    # result based on the oddest single word frequencies
    maxCovList = getFreqBasedWinner(db, maxCovList)

    return maxCovList


# this function finds the maximum frequency from a list of minimum frequency
def max_freq(var):
    m = var[0]
    for x, y in var:
        if y > m[1]:
            m = x, y
    return m


def setCover(currWord, remWords, passLength, sTime):
    '''Recursive algorithm to calculate the Set Cover for the words found in the password.
    Runs very slow for large numbers of input words.
    
    sTime -- pass the current time. If execution takes more than 60s, raises AllowedTimeExceededError
    
    '''
    ALLOWED_TIME = 60  # in seconds
    if time.time() - sTime > ALLOWED_TIME:
        raise AllowedTimeExceededError("SetCover function exceeded {}s".format(ALLOWED_TIME))

    if len(remWords) <= 1:
        if len(remWords) is 1:
            currWord.append(remWords[0])
        if len(currWord) is 1 and isinstance(currWord[0], str):
            return ([currWord], len(currWord))
        return ([currWord], evalLen(currWord))

    maxLenSet = list()
    maxLen = 0
    length = list()

    for x in remWords:
        if ((passLength - maxLen) < (x[1] - currWord[-1][2])):
            break  # short circuit to stop trying once we can't make a sequence that beats maxLen

        tempW = retWordLists(x, currWord, remWords)
        length = setCover(tempW[0], tempW[1], passLength, sTime)

        if length[1] == maxLen:
            for x in length[0]:
                if x not in maxLenSet:
                    maxLenSet.append(x)
        elif length[1] > maxLen:
            maxLen = length[1]
            maxLenSet = list()  # empty the list.
            for x in length[0]:
                if x not in maxLenSet:
                    maxLenSet.append(x)

    return (maxLenSet, maxLen)


def possibleTailStrings(currentWord, subList):
    '''Takes e_index from the current word, and subList of the remaining words.
    
    Returns the a list of original tuples that are non-overlapping with the 
    e_index of the current word.
    '''
    # debugging
    outList = list()
    for tup in subList:
        if tup[1] >= currentWord[2]:
            outList.append(tup)
    return outList  # returns the start and end index of words and returns the tupple like 0,3,che


def lastPassword():
    """ Returns the last password processed in the previous execution. """
    path = os.path.join(currentdir(), 'log_mineline.txt')
    with open(path, 'r') as f:
        id = int(f.readline())
    return id


def clearResults(dbe, pwset_id):
    with dbe.cursor() as cursor:
        # cursor.execute("TRUNCATE table set_contains;")
        cursor.execute("DELETE a FROM set_contains a INNER JOIN sets b on a.set_id = b.set_id \
             INNER JOIN passwords c on b.pass_id = c.pass_id and pwset_id = {};".format(pwset_id))
        # cursor.execute("ALTER TABLE set_contains AUTO_INCREMENT=1;")

        # cursor.execute("TRUNCATE table sets;")
        cursor.execute("DELETE a FROM sets a INNER JOIN passwords b on a.pass_id = b.pass_id \
            and pwset_id = {};".format(pwset_id))
        # cursor.execute("ALTER TABLE sets AUTO_INCREMENT=1;")


def currentdir():
    return os.path.dirname(os.path.abspath(__file__))


def between(x, y, z):
    '''if x is between y and z, return true, else false'''
    if x > y and x < z:
        return True
    else:
        return False

# Compiled regular expressions
reg_isint = re.compile("^[\d]+$")
reg_isNumAndSCChunk = re.compile("^[\W0-9_]+$")
reg_isSCChunk = re.compile("^[\W_]+$")
reg_isCharChunk = re.compile("^[a-zA-Z]+$")


def isInt(s):
    return bool(reg_isint.match(s))


def isNumAndSCChunk(s):
    return bool(reg_isNumAndSCChunk.match(s))


def isSCChunk(s):
    return bool(reg_isSCChunk.match(s))


def isCharChunk(s):
    return bool(reg_isCharChunk.match(s))


def reduceSubwords_v0_1(pwres):
    newPwres = list()
    currentsi = pwres[0][1]
    currentei = pwres[0][2]

    pwres = sorted(pwres, key=lambda word: word[1])

    # fix a start index; then pick the one with the furthest end index.
    # delete all others with that start index.
    for x in pwres:
        (xw, xsi, xei) = x
        topxs = x
        currentei = xei

        for r in pwres:
            (rw, rsi, rei) = r
            if (xsi == rsi and rei > currentei):
                topxs = r
                currentei = rei
        newPwres.append(topxs)

        # remove duplicates
    newPwres = list(set(newPwres))
    return newPwres


def tagChunk(s):
    if isInt(s):
        dynDictionaryID = NUM_DICT_ID
    elif isCharChunk(s):
        dynDictionaryID = CHAR_DICT_ID
    elif isSCChunk(s):
        dynDictionaryID = SC_DICT_ID
    elif isNumAndSCChunk(s):
        dynDictionaryID = MIXED_NUM_SC_DICT_ID
    else:
        dynDictionaryID = MIXED_ALL_DICT_ID
    return dynDictionaryID


def addInTheGapsHelper(db, retVal, i, password, lastEndIndex, nextStartIndex):
    # attention for the strip() call! space info is lost! who cares?!
    gap = password[lastEndIndex:nextStartIndex].strip()

    dynDictionaryID = tagChunk(gap)
    newLen = retVal[1]

    if ((len(gap) > 0) and (dynDictionaryID > 0)):
        addToDynamicDictionary(db, dynDictionaryID, gap)
        retVal[0][0].insert(i, (gap, lastEndIndex, nextStartIndex))
        newLen = newLen + (nextStartIndex - lastEndIndex)

    return (retVal[0], newLen)


def processGaps(db, resultSet, password):
    # scrutinize resultSet for sequence of numbers and special chars...
    # if any exist, add them into the dictionary table as a new entry
    # under dictset_id NUM_DICT_ID (for all numbers) and SC_DICT_ID (for all scs),
    # and MIXED_NUM_SC_DICT_ID (for a block of mixed numbers and scs).
    # Now we're also adding in garbage mixed everything under the id
    # CHAR_DICT_ID
    #
    # We add these gaps into the resultSet, at the relevant position.

    # New processing. Add pwd to dynamic dictionary as-is. No parsing.
    if (resultSet == []):
        resultSet = ([[(password, 0, len(password))]], len(password))
        dynDictionaryID = tagChunk(password)
        addToDynamicDictionary(db, dynDictionaryID, password)
    else:
        lastEndIndex = 0
        nextStartIndex = 0
        i = 0
        try:
            # iterates through the results. after the filtering by coverage
            # and frequency, there should be only one, though
            for result in resultSet[0]:
                for x in result:
                    (xw, xs, xe) = x
                    nextStartIndex = xs
                    if (nextStartIndex > lastEndIndex):
                        # find the gap, see if it is a #/sc chunk
                        resultSet = addInTheGapsHelper(db, resultSet, i, password, lastEndIndex, nextStartIndex)
                    lastEndIndex = xe
                    i = i + 1
                if (len(password) > lastEndIndex):
                    resultSet = addInTheGapsHelper(db, resultSet, i, password, lastEndIndex, len(password))
        except:
            print ("Warning: caught unknown error in addTheGaps -- resultSet=", resultSet, "password", password)

    return resultSet


def mineLine(db, password, dictionary, freqInfo):
    """Breaks a password in pieces, which can be words (present in the dictionaries) or sequences of
       numbers, symbols and characters that do not constitute a word.
    """

    # classifies password
    dynDictionaryID = tagChunk(password)

    # if contains only numbers and/or symbols, or contains only one character, 
    # insert it into the dyn. dictionary and don't try to parse
    if (dynDictionaryID != MIXED_ALL_DICT_ID and dynDictionaryID != CHAR_DICT_ID) \
            or (password.strip(password[0]) == ''):

        addToDynamicDictionary(db, dynDictionaryID, password)
        # Just return the password as-is; there is no word to be found.
        resultSet = ([[(password, 0, len(password))]], len(password))

    # Otherwise, try to find the best word-parsing
    else:
        permutations = permuteString(password.lower())
        words = list()
        for x in permutations:
            if x[0] in dictionary:
                words.append(x)

        candidates = generateCandidates(words, password)
        # print candidates
        resultSet = bestCandidate(db, password, candidates, freqInfo, dictionary)
        # print resultSet

        # add the trashy fragments in the database    
        resultSet = processGaps(db, resultSet, password)

    return resultSet


def generateCandidates(wordList, password):
    """ Takes a list of (possibly overlapping) words in form of tuples (word, s_index, e_index)
        and returns a list of candidate segmentations plus the corresponding coverage.
        For example:
        password: 'anybodyelse'
        
        wordList: [('any',0,3), ('anybody',0,7), ('body', 3, 7), ('else', 7, 11)]
        
        returns: [  ([[('any',0,3),('body', 3, 7),('else', 7, 11)]], 11),
                    ([[('anybody',0,6),('else', 7, 11)]], 11),
                    ([[('body', 3, 7),('else', 7, 11)]], 8)... ]

        This list includes segmentations with varied coverage.
        Don't ask me why the candidates contain that redudant list...
    """
    sublist = orderSortSubsList(wordList)
    if len(sublist) is 0:
        return sublist

    # sort by start index
    sortedList = sorted(wordList, key=lambda x: x[1])
    candidates = list()
    for x in sortedList:
        try:
            q = setCover([x], possibleTailStrings(x, sublist), len(password), time.time())
            candidates.append(q)
        except AllowedTimeExceededError, e:
            print str(e)
            print "SetCover failed for the following password: {}".format(password)
            candidates = list()
            break

    return candidates


def checkWebsiteSyntacticSimilarity(url1, url2):
    if url1.lower() == url2.lower():
        return True
    else:
        subDomainObjUrl1 = tldextract.extract(url1.lower())
        subDomainObjUrl2 = tldextract.extract(url2.lower())
        # first check whether domain and extension match
        if (subDomainObjUrl1.domain == subDomainObjUrl2.domain) and (subDomainObjUrl1.suffix == subDomainObjUrl2.suffix):
            # now check subdomain match
            if (subDomainObjUrl1.subdomain == subDomainObjUrl2.subdomain) or \
                    (subDomainObjUrl1.subdomain == "" and subDomainObjUrl2.subdomain == "www") or \
                    (subDomainObjUrl1.subdomain == "www" and subDomainObjUrl2.subdomain == ""):
                return True
            else:
                return False
        else:
            return False


def HTTPRequestHandlerContainer(freqInfo, dictionary, pos_tagger_data):
    global db, options, participantObj

    class HTTPRequestHandler(BaseHTTPRequestHandler):

        # handle POST command
        def do_POST(self):
            print self.path
            if "/website/save" in self.path:
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                postvars = self.get_post_data(ctype, pdict)
                if postvars != '':
                    websiteListData = json.loads(postvars['data'][0])

                    # save website list
                    insert_website_list(db, participantObj.get_participant_id(), websiteListData)
                    self.send_ok_response()
                else:
                    self.send_bad_request_response()

            elif "/participant/id" in self.path:
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                postvars = self.get_post_data(ctype, pdict)
                # set current active participant
                if postvars != '':
                    participantObj.set_participant_id(int(postvars['id'][0]))
                    self.send_ok_response()
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
                if "/participant/id" in self.path:
                    parsed = urlparse.urlparse(self.path)
                    one_way_hash = urlparse.parse_qs(parsed.query)['hash'][0]
                    participant_id = get_participant_id(db, one_way_hash)
                    participantObj.set_participant_id(participant_id)
                    self.send_ok_response(data=participant_id)

                elif "/transform" in self.path:
                    # getParams = self.path.split("transform?")[1]
                    parsed = urlparse.urlparse(self.path)
                    clearPassword = urlparse.parse_qs(parsed.query)['pass'][0]
                    clearUsername = urlparse.parse_qs(parsed.query)['user'][0]
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
                    transformed_password_id = get_transformed_password_id(db, participantObj.get_participant_id(), websiteUrl)

                    self.segmentPassword(clearPasswordURIDecoded)
                    self.posTagging()
                    self.grammarGeneration(transformed_password_id)

                    # Delete original password after transformation
                    self.clearOriginalData()

                    # Transform usernames semantically. We'll use the same functions for now.
                    # as the procedure is same, except that we dont have to store grammar.
                    self.segmentPassword(clearUsernameURIDecoded)
                    self.posTagging()
                    self.grammarGeneration(transformed_password_id, type="username")

                    self.clearOriginalData()

                    participantObj.reset_active_website()
                elif "/participant/results" in self.path:
                    parsed = urlparse.urlparse(self.path)
                    one_way_hash = urlparse.parse_qs(parsed.query)['hash'][0]
                    resultDict = get_transformed_passwords_results(db, one_way_hash)
                    self.send_ok_response(data=json.dumps(resultDict))
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
            self.send_header('Content-type', 'text-html')
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

        def segmentPassword(self, clearPassword):
            wbuff = WriteBuffer(db, dictionary, 100000)

            if len(clearPassword) == 0:
                return
            if clearPassword.strip(" ") == '':
                return

            # add Password to database temporarily.
            pass_id = addSocketPassword(db, clearPassword, participantObj.get_participant_id())

            res = mineLine(db, clearPassword, dictionary, freqInfo)
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
                             "../grammar3", options.tags, type=kwargs.get("type"))
            except KeyboardInterrupt:
                db.finish()
                raise


        def clearOriginalData(self):
            clear_original_data(db)


    return HTTPRequestHandler


def sqlMine(dictSetIds):
    '''Main function to mine the password set with the dictionary set.'''
    global db, options

    # offset = lastPassword() if options.cont else options.offset

    if options.reset:
        print "clearing results..."
        clearResults(db, participantObj.get_participant_id())

    print "caching frequency information"
    freqInfo = freqReadCache(db)

    print "loading n-grams..."
    with timer.Timer('n-grams load'):
        loadNgrams(db)

    if options.erase:
        print 'resetting dynamic dictionaries...'
        resetDynamicDictionary(db)

    print "reading dictionary..."
    dictionary = getDictionary(db, dictSetIds)

    print "Loading POS Tagger"
    with timer.Timer("Backoff tagger load"):
        picklePath = "../pickles/brown_clawstags.pickle"
        COCATaggerPath = "../../files/coca_500k.csv"

        pos_tagger_data = pos_tagger.BackoffTagger(picklePath, COCATaggerPath)


    server_address = ('127.0.0.1', 443)
    HTTPHandlerClass = HTTPRequestHandlerContainer(freqInfo, dictionary, pos_tagger_data)
    httpd = HTTPServer(server_address, HTTPHandlerClass)
    httpd.socket = ssl.wrap_socket(httpd.socket, certfile='C:\server.crt', server_side=True, keyfile='C:\server.key')
    print('https server is running...')
    httpd.serve_forever()


def main(opts):
    """I'm main."""
    # global dict_sets, USER, PASSWORD

    # USER = opts.user
    # PASSWORD = opts.pwd

    global db, options, participantObj
    db = connectToDb()
    options = opts
    participantObj = participant.Participant()
    sqlMine(dict_sets)


def cli_options():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--password_set', default=1, type=int,
                        help='the id of the collection of passwords to be processed')
    parser.add_argument('-v', '--verbose', action='store_true', help='prints every password processed')
    parser.add_argument('-e', '--erase', action='store_true', help='erase dynamic dictionaries')
    parser.add_argument('-r', '--reset', action='store_true',
                        help='reset results (truncates tables set and set_contains)')
    parser.add_argument('-d', '--dryrun', action='store_true', \
                        help="no commits to the database")
    parser.add_argument('-t', '--stats', action='store_true', \
                        help="output stats in the end")
    parser.add_argument('--tags', default='pos_semantic', \
                        choices=['pos_semantic', 'pos', 'backoff', 'word'])

    # db_group = parser.add_argument_group('Database Connection Arguments')
    # db_group.add_argument('--user', type=str, default='root', help="db username for authentication")
    # db_group.add_argument('--pwd',  type=str, default='', help="db pwd for authentication")
    # db_group.add_argument('--host', type=str, default='localhost', help="db host")
    # db_group.add_argument('--port', type=int, default=3306, help="db port")

    g = parser.add_mutually_exclusive_group()
    g.add_argument('-o', '--offset', type=int, default=0, help='skips processing N first passwords')
    g.add_argument('-c', '--cont', action='store_true', help='continue from the point it stopped previously')

    parser.add_argument('-s', '--sample', default=None, type=int, help='runs the algorithm for a limited sample')

    return parser.parse_args()


if __name__ == '__main__':
    options = cli_options()
    main(options)
