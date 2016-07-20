from server import SemtracServer

__author__ = 'Ameya'

server = SemtracServer()
db = server.get_db_conn()
cursor = server.get_db_cursor()


def get_unigram_freq():
    query = '''SELECT sum(freq) AS sum_freq FROM COCA_wordlist;'''
    cursor.execute(query)
    num_unigrams = cursor.fetchall()[0]['sum_freq']
    return num_unigrams


def get_bigram_freq():
    query = '''SELECT sum(freq) AS sum_freq FROM bigrams;'''
    cursor.execute(query)
    num_bigrams = cursor.fetchall()[0]['sum_freq']
    return num_bigrams


def get_trigram_freq():
    query = '''SELECT sum(freq) AS sum_freq FROM trigrams;'''
    cursor.execute(query)
    num_trigrams = cursor.fetchall()[0]['sum_freq']
    return num_trigrams


def get_unigrams():
    query = "SELECT word, MAX(freq) AS max_freq FROM passwords.COCA_wordlist GROUP BY word"
    cursor.execute(query)
    res = cursor.fetchall()
    return res


def get_dictionary_for_dictset(dictset_id):
    query = "SELECT dict_text, dict_id FROM dictionary WHERE dictset_id = {} ORDER BY dict_id ASC".format(dictset_id)
    cursor.execute(query)
    res = cursor.fetchall()
    return res


def get_last_id_sets():
    query = '''SELECT max(set_id) as max_set_id FROM sets;'''
    cursor.execute(query)
    res = cursor.fetchone()['max_set_id']
    return res


def get_dict_id_for_word(word):
    query = "SELECT dict_id FROM dictionary WHERE dict_text = '{}'".format(word)
    cursor.execute(query)
    res = cursor.fetchone()['dict_id']
    return res


def commit_db():
    db.commit()


def set_checks(value):
    cursor.execute("SET autocommit = {};".format(value))
    cursor.execute("SET unique_checks = {};".format(value))
    cursor.execute("SET foreign_key_checks = {};".format(value))


def insert_many_set(data):
    query = "INSERT INTO sets (pass_id, set_pw) VALUES (%s, %s)"
    cursor.executemany(query, data)
    db.commit()


def insert_many_set_contains(data):
    query = "INSERT INTO set_contains (set_id, dict_id, s_index, e_index) VALUES (%s,%s,%s,%s)"
    cursor.executemany(query, data)
    db.commit()


