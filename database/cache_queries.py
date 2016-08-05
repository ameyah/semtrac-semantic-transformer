from server import SemtracServer

__author__ = 'Ameya'

server = SemtracServer()
db = server.get_db_conn()


def get_unigram_freq():
    query = '''SELECT sum(freq) AS sum_freq FROM coca_wordlist;'''
    cursor = server.get_db_cursor()
    cursor.execute(query)
    num_unigrams = cursor.fetchall()[0]['sum_freq']
    cursor.close()
    return num_unigrams


def get_bigram_freq():
    query = '''SELECT sum(freq) AS sum_freq FROM bigrams;'''
    cursor = server.get_db_cursor()
    cursor.execute(query)
    num_bigrams = cursor.fetchall()[0]['sum_freq']
    cursor.close()
    return num_bigrams


def get_trigram_freq():
    query = '''SELECT sum(freq) AS sum_freq FROM trigrams;'''
    cursor = server.get_db_cursor()
    cursor.execute(query)
    num_trigrams = cursor.fetchall()[0]['sum_freq']
    cursor.close()
    return num_trigrams


def get_unigrams():
    query = "SELECT word, MAX(freq) AS max_freq FROM passwords.coca_wordlist GROUP BY word"
    cursor = server.get_db_cursor()
    cursor.execute(query)
    res = cursor.fetchall()
    cursor.close()
    return res


def get_dictionary_for_dictset(dictset_id):
    query = "SELECT dict_text, dict_id FROM dictionary WHERE dictset_id = {} ORDER BY dict_id ASC".format(dictset_id)
    cursor = server.get_db_cursor()
    cursor.execute(query)
    res = cursor.fetchall()
    cursor.close()
    return res


def get_last_id_sets():
    query = '''SELECT max(set_id) AS max_set_id FROM sets;'''
    cursor = server.get_db_cursor()
    cursor.execute(query)
    res = cursor.fetchone()['max_set_id']
    cursor.close()
    return res


def get_dict_id_for_word(word):
    query = "SELECT dict_id FROM dictionary WHERE dict_text = '{}'".format(word)
    cursor = server.get_db_cursor()
    cursor.execute(query)
    res = cursor.fetchone()['dict_id']
    cursor.close()
    return res


def commit_db():
    db.commit()


def set_checks(value):
    cursor = server.get_db_cursor()
    cursor.execute("SET autocommit = {};".format(value))
    cursor.execute("SET unique_checks = {};".format(value))
    cursor.execute("SET foreign_key_checks = {};".format(value))
    cursor.close()


def insert_many_set(data):
    query = "INSERT INTO sets (pass_id, set_pw) VALUES (%s, %s)"
    cursor = server.get_db_cursor()
    cursor.executemany(query, data)
    cursor.close()
    db.commit()


def insert_many_set_contains(data):
    query = "INSERT INTO set_contains (set_id, dict_id, s_index, e_index) VALUES (%s,%s,%s,%s)"
    cursor = server.get_db_cursor()
    cursor.executemany(query, data)
    cursor.close()
    db.commit()


def get_sets_count_for_participant(pwset_id):
    """ Retrieves the number of sets (segmentations) associated with a certain group
    of passwords.

    pwset_id - the id of the target group of passwords
    """

    query = "SELECT COUNT(*) AS count FROM sets LEFT JOIN passwords ON sets.pass_id = passwords.pass_id " \
            "WHERE passwords.pwset_id = {}".format(pwset_id)
    cursor = server.get_db_cursor()
    cursor.execute(query)
    count = cursor.fetchone()['count']
    cursor.close()
    return count


def get_word_segments(pwset_id, size):
    """ Returns all the segments.

    pwset_id - the id of the password set to be gathered
    """

    query = "SELECT sets.set_id AS set_id, " \
            "set_contains.id AS set_contains_id, dict_text, dictset_id, " \
            "pos, sentiment, synset, category, dictset_id, pass_text, s_index, e_index " \
            "FROM passwords " \
            "JOIN sets ON sets.pass_id = passwords.pass_id " \
            "JOIN set_contains ON set_contains.set_id = sets.set_id " \
            "JOIN dictionary ON set_contains.dict_id = dictionary.dict_id " \
            "WHERE passwords.pwset_id = {} ".format(pwset_id)
    cursor = server.get_db_cursor()
    cursor.execute(query)
    segments = cursor.fetchall()
    cursor.close()
    return segments


def extent_segments_parsed(pwset_id):
    """ Returns the SQL string to query the minimum and maximum pass_id (that have been parsed)
        from a group of passwords (determined by pwset_id). If no passwords have been parsed
        from the group, this query will return empty.
    """
    query = "SELECT MAX(pass_id) as max, MIN(pass_id) as min FROM sets LEFT JOIN passwords on sets.pass_id = passwords.pass_id " \
            "WHERE passwords.pwset_id = {}".format(pwset_id)
    cursor = server.get_db_cursor()
    cursor.execute(query)
    res = cursor.fetchone()
    cursor.close()
    return (res['max'], res['min'])


def update_set_contains(savebuffer):
    query = "UPDATE set_contains set pos=%s, sentiment=%s, synset=%s where id=%s;"
    cursor = server.get_db_cursor()
    cursor.executemany(query, savebuffer)
    cursor.close()
    db.commit()


def update_set_category(set_id, category):
    query = "UPDATE set_contains set category='{}' where id={}".format(category, set_id)
    cursor = server.get_db_cursor()
    cursor.execute(query)
    cursor.close()
    db.commit()