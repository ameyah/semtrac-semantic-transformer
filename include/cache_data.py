import pos_tagger

__author__ = 'Ameya'


class Cache():
    class __Cache():

        def __init__(self, db):
            self.db_conn = db
            self.db_cursor = db.get_cursor()

            # initialize variables
            self.freq_info = ()
            self.ngrams = dict()
            self.dictionary = dict()
            self.pos_tagger_data = None
            self.dict_sets = [10, 20, 30, 40, 60, 50, 80, 90]

        def cache_frequency_information(self):
            query = '''SELECT sum(freq) AS sum_freq FROM COCA_wordlist;'''
            self.db_cursor.execute(query)
            num_unigrams = self.db_cursor.fetchall()[0]['sum_freq']
            query = '''SELECT sum(freq) AS sum_freq FROM bigrams;'''
            self.db_cursor.execute(query)
            num_bigrams = self.db_cursor.fetchall()[0]['sum_freq']
            query = '''SELECT sum(freq) AS sum_freq FROM trigrams;'''
            self.db_cursor.execute(query)
            num_trigrams = self.db_cursor.fetchall()[0]['sum_freq']

            self.freq_info = (num_unigrams, num_bigrams, num_trigrams)

        def cache_n_grams(self):
            # load unigrams
            query = 'SELECT word, MAX(freq) AS max_freq FROM passwords.COCA_wordlist GROUP BY word'
            self.db_cursor.execute(query)
            res = self.db_cursor.fetchall()
            for freq_info in res:
                self.ngrams[freq_info['word']] = freq_info['max_freq']

            # TODO: if used, format the code to convert from oursql to MySQLDb
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

        def cache_dictionary(self):
            query = "SELECT dict_text, dict_id FROM dictionary WHERE dictset_id = {} ORDER BY dict_id ASC;"
            for x in self.dict_sets:
                temp_query = query.format(x)
                self.db_cursor.execute(temp_query)
                res = self.db_cursor.fetchall()
                # THIS PRIORITIZES DICTIONARIES.
                # assumption: the dictionaries are in priority order (in the dictset_ids list)
                for dict_info in res:
                    try:
                        tmp = self.dictionary[dict_info['dict_text'].lower()]
                    except KeyError:
                        self.dictionary[dict_info['dict_text'].lower()] = (x, dict_info['dict_id'])
            print("dictionary length:", len(self.dictionary))

        def load_pos_tagger(self, pickle_path, coca_tagger_path):
            self.pos_tagger_data = pos_tagger.BackoffTagger(pickle_path, coca_tagger_path)

    __instance = None

    def __init__(self, db):
        if Cache.__instance is None:
            Cache.__instance = Cache.__Cache(db)
        self.__dict__['Cache__instance'] = Cache.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)