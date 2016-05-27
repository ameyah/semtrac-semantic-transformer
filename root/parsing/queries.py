from oursql import CollatedWarningsError
import datetime
import tldextract
from dictionary_trie import Trie
from utils import *
from dateutil import parser

NUM_DICT_ID    = 200
MIXED_NUM_SC_DICT_ID = 201
SC_DICT_ID = 202
CHAR_DICT_ID = 203
MIXED_ALL_DICT_ID = 204

# trie     = Trie()

ngrams = dict()

toEscape = ['\\', '\'', ' ']

# the Trie, at least in the way I implemented, is a SUPER FAILURE
# in terms of memory consumption
# def initializeTrie(dbe):
# 
#     # populating our unigram trie
#     with dbe.cursor() as cursor:
#             query = 'SELECT word,MAX(freq) FROM passwords.COCA_wordlist group by word'
#             cursor.execute(query, )
#             for word, freq in cursor:
#                     trie.insert(word, freq)
#             cursor.close()
#     # then the bigram trie        
#     with dbe.cursor() as cursor:
#             query = 'SELECT word1, word2, freq FROM passwords.bigrams'
#             cursor.execute(query, )
#             for word1, word2, freq in cursor:
#                     trie.insert(word1+' '+word2, freq)
#             cursor.close()
#     # then the trigram trie        
#     with dbe.cursor() as cursor:
#             query = 'SELECT word1, word2, word3, freq FROM passwords.trigrams'
#             cursor.execute(query, )
#             for word1, word2, word3, freq in cursor:
#                     trie.insert(word1+' '+word2+' '+word3, freq)
#             cursor.close()

# def storeTrieInFile():
#     trie.saveState('coca_trie.pik')

def loadNgrams(dbe):
    # unigrams
    with dbe.cursor() as cursor:
        query = 'SELECT word, MAX(freq) FROM passwords.COCA_wordlist group by word'
        cursor.execute(query, )
        for word, freq in cursor:
            ngrams[word] = freq
        cursor.close()
    
    """
    # bigrams
    with dbe.cursor() as cursor:
        query = 'SELECT word1, word2, freq FROM passwords.bigrams'
        cursor.execute(query, )
        for word1, word2, freq in cursor:
                ngrams[word1+' '+word2] = freq
        cursor.close()
    
    # trigrams        
    with dbe.cursor() as cursor:
        query = 'SELECT word1, word2, word3, freq FROM passwords.trigrams'
        cursor.execute(query, )
        for word1, word2, word3, freq in cursor:
            ngrams[word1+' '+word2+' '+word3] = freq
        cursor.close()

    """

def getDataSetSize(dbe, tableName):

    with dbe.cursor() as cursor:
        query = '''SELECT count(*) FROM ''' + tableName + ''';'''
        cursor.execute(query, )
        count = cursor.fetchall()[0][0]
        cursor.close()
        
    return count

def freqReadCache(dbe):

    # we actually need to sum these up to be accurate, instead of just their
    # raw count.
    with dbe.cursor() as cursor:
        query = '''SELECT sum(freq) FROM COCA_wordlist;'''
        cursor.execute(query, )
        num_unigrams = cursor.fetchall()[0][0]
        query = '''SELECT sum(freq) FROM bigrams;'''
        cursor.execute(query, )
        num_bigrams = cursor.fetchall()[0][0]
        query = '''SELECT sum(freq) FROM trigrams;'''
        cursor.execute(query, )
        num_trigrams = cursor.fetchall()[0][0]

        cursor.close()
        
    return (num_unigrams, num_bigrams, num_trigrams)

def resetDynamicDictionary( dbe ):
    query = '''DELETE FROM dictionary where dictset_id >= ''' + str(NUM_DICT_ID) + ''';'''
    with dbe.cursor() as cur:
        cur.execute(query, ())

def reloadDynamicDictionary(dbe, oldDictionary):
    result = getDictionary(dbe, [NUM_DICT_ID, MIXED_NUM_SC_DICT_ID, SC_DICT_ID, CHAR_DICT_ID])
    for x in result:
        oldDictionary[x] = result[x]
        #print ("reloadDictionary: ", x, ":", oldDictionary[x])

    #print ("test: ", oldDictionary[u'D'])
    return oldDictionary

def addToDynamicDictionary(dbe, dynDictionaryID, segment):
    '''Adds a segment to the db with a certain dictset_id.
    Notice that it won't make the segment lowercase; so 'lWic' ~= 'lwic'.
    It will, however, strip it, i.e., 'lwic  ' == 'lwic'    
    '''
    # right-strip it cause MySQL doesn't consider trailing spaces
    segment = segment.rstrip()

    query = '''INSERT INTO dictionary (dictset_id, dict_text)
    select * from (select ''' + str(dynDictionaryID) + ''' as id,  \'''' + escape(segment, toEscape) + '''\' as text  )
    as tmp where not exists (select dictset_id, dict_text from dictionary where
    dictset_id = ? and dict_text = ?);'''

    with dbe.cursor() as cur:
        cur.execute(query, (dynDictionaryID, segment,))

#     cur.close()  # no need for this
    
    # Apparently we don't need to return the dynDictID
#     result = dictIDbyWord(dbe, [segment], dynDictionaryID)
#     try:
#         dynDictID = result[segment]
#     except KeyError, e:
#         print 'KeyError -> segment: ', segment, ' not found in: ', result
#         raise
#     return dynDictID

def addSocketPassword(sqleng, password, pwsetID):
    with sqleng.cursor() as cursor:
        query = '''INSERT INTO passwords
                SET pwset_id = ?, pass_text = ?;'''
        cursor.execute(query, params=(pwsetID, escape(password, toEscape)))
        query = '''SELECT LAST_INSERT_ID();'''
        cursor.execute(query)
        pwid = cursor.fetchall()[0][0]
        cursor.close()
    return pwid

def pwIDfromText(sqleng, password, pwsetID):
    '''Not used anymore'''
    with sqleng.cursor() as cursor:
        query = '''SELECT pass_id FROM passwords
                WHERE pwset_id = ? AND pass_text = ?
                LIMIT 1;'''
        cursor.execute(query, params=(pwsetID, escape(password, toEscape)))
        pwid = cursor.fetchall()[0][0]
        cursor.close()
    return pwid

def dictIDbyWord(sqleng, dictwordset, dictsetID=None):
    result = dict()
    
    query = '''SELECT dict_id, dict_text FROM dictionary
                WHERE dict_text = ?'''
    if dictsetID :
        query += ''' AND dictset_id = ?;'''
    
    with sqleng.cursor() as cur:
        for x in dictwordset:
            params = (x, dictsetID) if dictsetID else (x,)
            cur.execute(query, params)
            for dict_id, dict_text in cur:
                result[dict_text] = dict_id
    return result
        
def partIter(iterable, const):
    '''A partial iterator, outputs the constant value with each of the iterable.'''
    pool = tuple(iterable)
    for x in pool:
        yield (const, x)

def resIter(setID, resSet, idMap):
    '''Iterator generator used for storing the results. A nice little generator.'''
    pool = tuple(resSet)
    for x in pool:
        yield (setID, idMap[x[0]][1], x[1], x[2])

def wordsFromResultSet(resultSet):
    '''Returns just the words for the result set, for use in storage.'''
    words = list()
    for sets in resultSet[0]:
        for wordTups in sets:
            if wordTups[0] not in words:
                words.append(wordTups[0])
    return words
        
def storeResults(sqleng, passID, dictsetID, resultSet, dictionary):
    '''Older function used to store the results into the database, depreciated.'''
    words = wordsFromResultSet(resultSet) #gets s simple list of all words in resultSet
    print(words)
    dwords = dictionary
    sets = dict() #this is supposed to be dict[set#] = "string of pass"
    for x in range(len(resultSet[0])): #i hate iterating this way =/
        setext = ''
        for wordTup in resultSet[0][x]:
            setext += wordTup[0]
        sets[x] = setext
    
    print("sets:",sets)
    print("rs:",resultSet)
    print()
    
    insQuery = '''INSERT INTO sets (pass_id, set_pw) VALUES ( ? , ? );'''
    linkQuery = '''INSERT INTO set_contains (set_id, dict_id, s_index, e_index) VALUES
            ( ? , ? , ? , ? );'''
    
    with sqleng.cursor() as cur:
        for x in range(len(sets)):
            #this is where all the time is comming from.
            cur.execute(insQuery, (passID, sets[x]))
            rid = cur.lastrowid
            cur.executemany(linkQuery, resIter(rid, resultSet[0][x], dwords)) #i hopes this is right

def getDictionary(sqleng, dictset_ids):
    
    query = '''SELECT dict_text, dict_id FROM dictionary WHERE dictset_id = ?
            ORDER BY dict_id asc;'''
    dictionary = dict()
    tmp = None # for throwing keyerrors on dicitonary
    with sqleng.cursor() as cur:
        #this execution should be more or less 30 seconds for the size of DB currently.
        for x in dictset_ids:
            #print ("X=", x)
            cur.execute(query, (x,))
            res = cur.fetchall()
            ## THIS PRIORITIZES DICTIONARIES.
            ## assumption: the dictionaries are in priority order (in the dictset_ids list)
            for dict_text, dict_id in res:
                try: 
                    tmp = dictionary[dict_text.lower()]
                except:
                    # TODO: This change is experimental. *Apparently*, we don't need dict_text in the tuple,
                    # but the guessability code needs dictset_id  
#                     dictionary[dict_text] = (dict_text, dict_id)
                    dictionary[dict_text.lower()] = (x, dict_id)
    print("dictionary length:",len(dictionary))
    return dictionary
    

def passCount(dbe, passSetID):
    '''Not used anymore.'''
    query = '''SELECT count(*) FROM passwords WHERE pwset_id = ?'''
    with dbe.cursor() as cur:
        cur.execute(query, (passSetID,))
        count = cur.fetchone()[0]
    return count
            
def getFreq (dbe, word):
    return 0 if word not in ngrams else ngrams[word]
    
#     return trie.getFrequency(theWord)
        
#    query = '''SELECT MAX(freq) from COCA_wordlist WHERE word = ?'''
#    with dbe.cursor() as cur:
#        cur.execute(query, (theWord,))
#        freq = cur.fetchone()[0]
#        if not freq:
#            freq = 0
#    return freq;

def getBigramFreq (dbe, word1, word2):
    key = ' '.join([word1, word2])
    return 0 if key not in ngrams else ngrams[key]
 
#     return trie.getFrequency(word1+' '+word2)

#    query = '''SELECT MAX(freq) from bigrams WHERE word1 = ? and word2 = ?'''
#    with dbe.cursor() as cur:
#        cur.execute(query, (word1, word2,))
#        freq = cur.fetchone()[0]
#        if not freq:
#            freq = 0
#    return freq;

def getTrigramFreq (dbe, word1, word2, word3):
    key = ' '.join([word1, word2, word3])
    return 0 if key not in ngrams else ngrams[key]

#     return trie.getFrequency(word1+' '+word2+' '+word3)

#    query = '''SELECT MAX(freq) from trigrams WHERE word1 = ? and word2 = ? and word3=?'''
#    with dbe.cursor() as cur:
#        cur.execute(query, (word1, word2, word3))
#        freq = cur.fetchone()[0]
#        if not freq:
#            freq = 0
#    return freq;


def check_website_exists(db, website_url):
    """Returns website_id of a website_url if it exists"""
    website_id = None
    query = '''SELECT website_id FROM websites WHERE website_text = ?'''
    with db.cursor() as cur:
        cur.execute(query, (website_url,))
        res = cur.fetchall()
        if len(res) > 0:
            website_id = res[0][0]
        else:
            # check if website_url contains "www."
            subDomainObj = tldextract.extract(website_url)
            if subDomainObj.subdomain.lower() == "www":
                with db.cursor() as cur:
                    domainText = "{}.{}".format(subDomainObj.domain, subDomainObj.suffix)
                    cur.execute(query, (domainText,))
                    res = cur.fetchall()
                    if len(res) > 0:
                        website_id = res[0][0]

    return website_id


def add_website(db, website_url):
    website_id = None
    query = '''INSERT INTO websites SET website_text = ?'''
    with db.cursor() as cur:
        cur.execute(query, (website_url,))
        query = '''SELECT website_id FROM websites WHERE website_text = ?'''
        with db.cursor() as cur:
            cur.execute(query, (website_url,))
            website_id = cur.fetchall()[0][0]
    return website_id


def get_transformed_password_id(db, password_set, website_url):
    """Returns id of transformed_passwords table corresponding to password_set and website_url
    This function first grabs website_id from website_url and then queries transformed_passwords table
    for transformed_password ID.
    Modification: Grab the transformed_password ID for row which doesn't have password_text set
    satisfying the above conditions. If there is no such row, insert it."""

    website_id = check_website_exists(db, website_url)

    if website_id is None:
        # add the website and fetch website_id
        website_id = add_website(db, website_url)

    query = '''SELECT password_id FROM transformed_passwords WHERE pwset_id=? AND website_id=? AND password_text is NULL'''
    with db.cursor() as cur:
        cur.execute(query, (password_set, website_id,))
        res = cur.fetchall()
        if len(res) > 0:
            password_id = res[0][0]
            return password_id
        else:
            # Create new entry in transformed_passwords
            query = '''INSERT INTO transformed_passwords SET website_id = ?, pwset_id = ?'''
            with db.cursor() as cur:
                cur.execute(query, (website_id, password_set,))
                query = '''SELECT password_id FROM transformed_passwords WHERE website_id = ? AND pwset_id = ? AND password_text is NULL'''
                with db.cursor() as cur:
                    cur.execute(query, (website_id, password_set,))
                    password_id = cur.fetchall()[0][0]
                    return password_id


def clear_original_data(db):
    query = '''DELETE FROM passwords.passwords'''
    with db.cursor() as cur:
        cur.execute(query)
    query = '''DELETE FROM sets'''
    with db.cursor() as cur:
        cur.execute(query)
    query = '''DELETE FROM set_contains'''
    with db.cursor() as cur:
        cur.execute(query)


def insert_website_list(db, participant_id, website_list):
    # Remove previous entries of same participant_id
    query = '''DELETE FROM transformed_passwords WHERE pwset_id = ?'''
    with db.cursor() as cur:
        cur.execute(query, (participant_id,))

    for website in website_list:
        url = website['url']
        website_id = check_website_exists(db, url)

        if website_id is None:
            # add the website and fetch website_id
            website_id = add_website(db, url)

        # Now, we have website_id
        # Convert date time string to datetime object
        # dateTimeFormat = '%a, %d %b %Y %H:%M:%S %z'
        dateTimeObj = parser.parse(website['date'])

        query = '''INSERT INTO transformed_passwords SET pwset_id = ?, website_id = ?, password_reset_count = ?, date = ?'''
        with db.cursor() as cur:
            cur.execute(query, (participant_id, website_id, website['reset_count'], dateTimeObj,))


def get_participant_id(db, one_way_hash):
    # Insert new participant ID
    cursor = db.cursor()
    query = "SELECT pwset_id FROM password_set WHERE pwset_name='" + one_way_hash + "'"
    cursor.execute(query)
    if cursor.rowcount > 0:
        return cursor.fetchone()[0]
    else:
        query = "INSERT INTO password_set SET pwset_name='" + one_way_hash + "', max_pass_length=50"
        cursor.execute(query)
        db.commit()
        query = "SELECT pwset_id FROM password_set WHERE pwset_name='" + one_way_hash + "'"
        cursor.execute(query)
        return cursor.fetchone()[0]


def get_transformed_passwords_results(db, one_way_hash):
    participant_id = get_participant_id(db, one_way_hash)

    query = '''SELECT website_id, password_reset_count, password_text FROM transformed_passwords WHERE pwset_id = ? ORDER BY website_id'''
    with db.cursor() as cur:
        cur.execute(query, (participant_id,))
        res = cur.fetchall()
        if len(res) > 0:
            transformed_passwords = res
            # convert list of tuples to list of lists
            transformed_passwords = [list(elem) for elem in transformed_passwords]
            for passwordArr in transformed_passwords:
                website_id = int(passwordArr[0])
                query = '''SELECT website_text FROM websites WHERE website_id = ?'''
                with db.cursor() as cur:
                    cur.execute(query, (website_id,))
                    website_text = cur.fetchall()[0][0]
                    passwordArr[0] = website_text

            resultDict = {
                'participant_id': participant_id,
                'transformed_passwords': transformed_passwords
            }
            return resultDict
        else:
            resultDict = {
                'participant_id': participant_id
            }
            return resultDict