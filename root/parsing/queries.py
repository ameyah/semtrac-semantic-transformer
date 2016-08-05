from oursql import CollatedWarningsError
import datetime
import tldextract
from dictionary_trie import Trie
from utils import *
from dateutil import parser
import unicodedata


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
        query = 'SELECT word, MAX(freq) FROM passwords.coca_wordlist group by word'
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
        query = '''SELECT sum(freq) FROM coca_wordlist;'''
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
            # check if website_url contains "www." or sub domain is blank
            subDomainObj = tldextract.extract(website_url)
            if subDomainObj.subdomain.lower() == "www":
                with db.cursor() as cur:
                    domainText = "{}.{}".format(subDomainObj.domain, subDomainObj.suffix)
                    cur.execute(query, (domainText,))
                    res = cur.fetchall()
                    if len(res) > 0:
                        website_id = res[0][0]
            elif subDomainObj.subdomain.lower() == "":
                domainText = "www.{}.{}".format(subDomainObj.domain, subDomainObj.suffix)
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


def get_transformed_credentials_id(db, password_set, website_url, password_strength, password_warning):
    """Returns id of transformed_credentials table corresponding to password_set and website_url of user_websites table
    This function first grabs website_id from website_url and then queries user_websites table
    for user_website_id ID."""

    website_id = check_website_exists(db, website_url)

    if website_id is None:
        # add the website and fetch website_id
        website_id = add_website(db, website_url)

    query = '''SELECT user_website_id FROM user_websites WHERE pwset_id=? AND website_id=?'''
    with db.cursor() as cur:
        cur.execute(query, (password_set, website_id,))
        res = cur.fetchall()
        if len(res) > 0:
            user_website_id = res[0][0]
        else:
            # Create new entry in user_websites table
            query = '''INSERT INTO user_websites SET website_id = ?, pwset_id = ?'''
            cur.execute(query, (website_id, password_set,))
            query = '''SELECT user_website_id FROM user_websites WHERE website_id = ? AND pwset_id = ?'''
            cur.execute(query, (website_id, password_set,))
            user_website_id = cur.fetchall()[0][0]
        # Assuming we now have user_website_id
        # Insert new row in transformed_credentials table and return the transformed_cred_id
        query = '''INSERT INTO transformed_credentials SET user_website_id = ?, password_strength = ?, password_warning = ?'''
        cur.execute(query, (user_website_id, float(password_strength), escape(password_warning, toEscape),))
        query = '''SELECT transformed_cred_id FROM transformed_credentials WHERE user_website_id = ? ORDER BY
                transformed_cred_id DESC LIMIT 1'''
        cur.execute(query, (user_website_id,))
        transformed_cred_id = cur.fetchall()[0][0]
        return transformed_cred_id


def clear_original_data(db):
    query = '''DELETE FROM passwords.passwords'''
    with db.cursor() as cur:
        cur.execute(query)
        query = '''DELETE FROM sets'''
        cur.execute(query)
        query = '''DELETE FROM set_contains'''
        cur.execute(query)


def clear_password_key(db):
    query = '''UPDATE password_set SET password_key = NULL'''
    with db.cursor() as cur:
        cur.execute(query)


def insert_website_list(db, participant_id, website_list):
    # Reset website importance probabilities
    # reset_website_probability(db, participant_id)
    # Remove previous entries of same participant_id
    # query = '''DELETE FROM transformed_passwords WHERE pwset_id = ?'''
    # with db.cursor() as cur:
    #     cur.execute(query, (participant_id,))

    new_website_id_list = ()
    for website in website_list:
        try:
            url = website['url']
            website_id = check_website_exists(db, url)

            if website_id is None:
                # add the website and fetch website_id
                website_id = add_website(db, url)

            new_website_id_list += (int(website_id),)
            # Now, we have website_id
            # Convert date time string to datetime object
            # dateTimeFormat = '%a, %d %b %Y %H:%M:%S %z'
            null_date_flag = False
            if str(website['date']) is "":
                null_date_flag = True
            else:
                try:
                    dateTimeObj = parser.parse(website['date'])
                except ValueError:
                    print "date exception"
                    dateTimeObj = parser.parse(website['date'].split("(")[0])

            website_user_probability = 1 if website['important'] else 0

            # First check if entry exists in transformed_passwords table, update it else insert new entry
            query = '''SELECT user_website_id FROM user_websites WHERE pwset_id = ? AND website_id = ?'''
            with db.cursor() as cur:
                cur.execute(query, (participant_id, website_id,))
                user_website_row = cur.fetchall()
                if len(user_website_row) > 0:
                    if null_date_flag:
                        query = '''UPDATE user_websites SET website_probability = ?, password_reset_count = ? WHERE user_website_id = ?'''
                        cur.execute(query, (website_user_probability, website['reset_count'], user_website_row[0][0],))
                    else:
                        query = '''UPDATE user_websites SET website_probability = ?, password_reset_count = ?, date = ? WHERE user_website_id = ?'''
                        cur.execute(query, (website_user_probability, website['reset_count'], dateTimeObj, user_website_row[0][0],))
                else:
                    query = '''INSERT INTO user_websites SET pwset_id = ?, website_id = ?, website_probability=?, password_reset_count = ?, date = ?'''
                    cur.execute(query, (participant_id, website_id, website_user_probability, website['reset_count'], dateTimeObj,))

                # calculate new probability and store it
                """
                query = '''SELECT probability, p_users FROM websites WHERE website_id=?'''
                with db.cursor() as cur:
                    cur.execute(query, (website_id,))
                    website_info = cur.fetchall()[0]
                    new_probability = calculate_new_probability_add_user(website_info[0], website_info[1], website_user_probability)
                    query = '''UPDATE websites SET probability=?, p_users=? WHERE website_id=?'''
                    cur.execute(query, (new_probability, (website_info[1] + 1), website_id,))
                """
        except:
            print "exception"
            continue

    # Now remove the websites present in database, but not in newly received website_list and websites which dont have
    # any password associated with them
    if len(new_website_id_list) == 1:
        # to remove the trailing comma
        website_id_list_str = "(" + str(new_website_id_list[0]) + ")"
    else:
        website_id_list_str = str(new_website_id_list)
    query = '''SELECT DISTINCT user_website_id FROM transformed_credentials'''
    with db.cursor() as cur:
        cur.execute(query)
        website_ids = cur.fetchall()
        not_user_website_ids = ()
        if len(website_ids) == 1:
            # to remove the trailing comma
            not_user_website_ids = "(" + str(int(website_ids[0][0])) + ")"
        else:
            for id in website_ids:
                not_user_website_ids += (int(id[0]),)
        if len(new_website_id_list) == 0:
            if len(website_ids) == 0:
                query = '''DELETE FROM user_websites WHERE pwset_id = ?'''
            else:
                query = '''DELETE FROM user_websites WHERE pwset_id = ? and user_website_id not in {}'''.format(str(not_user_website_ids))
        elif len(website_ids) == 0:
            query = '''DELETE FROM user_websites WHERE pwset_id = ? and website_id not in {}'''.format(website_id_list_str)
        else:
            query = '''DELETE FROM user_websites WHERE pwset_id = ? and website_id not in {} and user_website_id not in {}'''.format(website_id_list_str, str(not_user_website_ids))
        print query
        cur.execute(query, (participant_id,))


def get_participant_id(db, one_way_hash):
    # Insert new participant ID
    cursor = db.cursor()
    query = "SELECT pwset_id FROM password_set WHERE pwset_name='" + one_way_hash + "'"
    cursor.execute(query)
    res = cursor.fetchone()
    if res is not None:
        return res[0]
    else:
        query = "INSERT INTO password_set SET pwset_name='" + one_way_hash + "', max_pass_length=50"
        cursor.execute(query)
        db.commit()
        query = "SELECT pwset_id FROM password_set WHERE pwset_name='" + one_way_hash + "'"
        cursor.execute(query)
        return cursor.fetchone()[0]


def get_transformed_passwords_results(db, one_way_hash):
    participant_id = get_participant_id(db, one_way_hash)

    query = '''SELECT user_websites.website_id, user_websites.website_probability, user_websites.password_reset_count,
            transformed_credentials.username_text, transformed_credentials.password_text, grammar.grammar_text,
            transformed_credentials.auth_status FROM user_websites INNER JOIN transformed_credentials ON user_websites.user_website_id = transformed_credentials.user_website_id
            JOIN grammar ON transformed_credentials.password_grammar_id = grammar.grammar_id WHERE
            user_websites.pwset_id = ? ORDER BY user_websites.website_id'''
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


def get_website_probability(db, website_url):
    website_id = check_website_exists(db, website_url)
    if website_id is not None:
        query = '''SELECT probability FROM websites WHERE website_id=?'''
        with db.cursor() as cur:
            cur.execute(query, (website_id,))
            if cur.fetchall()[0][0] >= 0.50:
                return True
            else:
                return False
    else:
        return None


def get_website_list_probability(db, website_list):
    website_list_info = []
    for website in website_list:
        url = website['url']
        importance = get_website_probability(db, url)
        if importance is not None:
            website_info = {
                'id': website['id'],
                'url': url,
                'important': importance
            }
            website_list_info.append(website_info)
    return website_list_info


def reset_website_probability(db, participant_id):
    query = '''SELECT website_id, website_probability FROM transformed_passwords WHERE pwset_id=?'''
    with db.cursor() as cur:
        cur.execute(query, (participant_id,))
        user_websites_info = cur.fetchall()
        if len(user_websites_info) > 0:
            for user_website in user_websites_info:
                query = '''SELECT probability, p_users FROM websites WHERE website_id=?'''
                cur.execute(query, (user_website[0],))
                websites_info = cur.fetchall()[0]
                new_probability = calculate_new_probability_remove_user(websites_info[0], websites_info[1], user_website[1])
                if new_probability is None:
                    new_probability = 0
                # update the probability and number of users in websites table
                query = '''UPDATE websites SET probability=?, p_users=? WHERE website_id=?'''
                cur.execute(query, (new_probability, (websites_info[1] - 1), user_website[0],))


def save_auth_status(db, transformed_cred_id, status):
    query = '''UPDATE transformed_credentials SET auth_status = ? WHERE transformed_cred_id = ?'''
    with db.cursor() as cur:
        cur.execute(query, (status, transformed_cred_id,))


def make_password_same(db, participant_id, transformed_cred_id, hash_index):
    query = '''SELECT password_text FROM transformed_credentials INNER JOIN user_websites WHERE
            transformed_credentials.user_website_id = user_websites.user_website_id AND user_websites.pwset_id=? AND
            transformed_credentials.password_similarity=? LIMIT 1'''
    with db.cursor() as cur:
        cur.execute(query, (participant_id, hash_index,))
        try:
            old_password = cur.fetchall()[0][0]
            query = '''UPDATE transformed_credentials SET password_text=? WHERE transformed_cred_id=?'''
            cur.execute(query, (old_password, transformed_cred_id,))
        except IndexError:
            return None


def append_email_domain(db, transformed_cred_id, email_domain):
    query = '''SELECT username_text FROM transformed_credentials WHERE transformed_cred_id=?'''
    with db.cursor() as cur:
        cur.execute(query, (transformed_cred_id,))
        res = cur.fetchall()
        if len(res) > 0:
            old_username = res[0][0]
            if old_username is not None:
                # append email_domain to old_username
                new_username = old_username + str(email_domain)
                query = '''UPDATE transformed_credentials SET username_text = ? WHERE transformed_cred_id=?'''
                cur.execute(query, (new_username, transformed_cred_id,))


def get_study_questions(db, participant_id, questions_type):
    if questions_type == "CURRENT" or questions_type == "RISK" or questions_type == "POST":
        query = '''SELECT question_id, question FROM study_questions WHERE type=? ORDER BY question_id'''
        with db.cursor() as cur:
            cur.execute(query, (questions_type,))
            questions = cur.fetchall()
            questions = [{"question_id": int(elem[0]), "question": unicodedata.normalize('NFKD', elem[1]).encode('ascii','ignore')} for elem in questions]
            if len(questions) > 0:
                if questions_type == "POST":
                    query = '''SELECT website_id, website_text FROM websites WHERE website_id IN (SELECT DISTINCT
                    website_id FROM user_websites INNER JOIN transformed_credentials WHERE user_websites.user_website_id =
                    transformed_credentials.user_website_id AND pwset_id = ?)'''
                    cur.execute(query, (participant_id,))
                    websites = cur.fetchall()
                    result_obj = {
                        "questions": questions,
                        "websites": []
                    }
                    for website in websites:
                        website_obj = {
                            "id": website[0],
                            "text": website[1]
                        }
                        result_obj['websites'].append(website_obj)
                    return result_obj
                return questions


def insert_prestudy_answers(db, participant_id, answers):
    for answer in answers:
        if 0 < answer['answer'] < 6:
            query = '''DELETE FROM study_responses WHERE pwset_id = ? AND question_id = ?'''
            with db.cursor() as cur:
                cur.execute(query, (participant_id, answer['question_id'],))
                query = '''INSERT INTO study_responses SET pwset_id = ?, question_id = ?, response_obj = ?'''
                cur.execute(query, (participant_id, answer['question_id'], answer['answer'],))
        else:
            return None

    return 1


def insert_poststudy_answers(db, participant_id, answers):
    for answer in answers:
        if 0 < answer['answer'] < 6:
            query = '''DELETE FROM study_responses WHERE pwset_id = ? AND question_id = ? AND website_id = ?'''
            with db.cursor() as cur:
                cur.execute(query, (participant_id, answer['question_id'], answer['website_id'],))
                query = '''INSERT INTO study_responses SET pwset_id = ?, question_id = ?, website_id = ?, response_obj = ?'''
                cur.execute(query, (participant_id, answer['question_id'], answer['website_id'], answer['answer'],))
        else:
            return None

    return 1


def add_new_website(db, participant_id, website_url, website_importance):
    website_id = check_website_exists(db, website_url)
    if website_id is None:
        # add the website and fetch website_id
        website_id = add_website(db, website_url)
    query = '''SELECT user_website_id FROM user_websites WHERE pwset_id = ? AND website_id = ?'''
    with db.cursor() as cur:
        cur.execute(query, (participant_id, website_id,))
        res = cur.fetchall()
        if len(res) > 0:
            query = '''UPDATE user_websites SET website_probability = ? WHERE user_website_id = ?'''
            cur.execute(query, (int(website_importance), int(res[0][0]),))
            return 1
    query = '''INSERT INTO user_websites SET pwset_id = ?, website_id = ?, website_probability = ?'''
    with db.cursor() as cur:
        cur.execute(query, (participant_id, website_id, website_importance,))
        return 1