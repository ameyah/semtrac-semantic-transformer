import pos_tagger
from server import SemtracServer
import database.cache_queries as cache_queries

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
            num_unigrams = cache_queries.get_unigram_freq()
            num_bigrams = cache_queries.get_bigram_freq()
            num_trigrams = cache_queries.get_trigram_freq()
            self.freq_info = (num_unigrams, num_bigrams, num_trigrams)

        def cache_n_grams(self):
            # load unigrams
            res = cache_queries.get_unigrams()
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
            for x in self.dict_sets:
                res = cache_queries.get_dictionary_for_dictset(x)
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


class TempClearTextWriteBuffer(object):
    """A buffering class for sql writes, to speed everything up nicely. Stores the clear text credentials and its
    associated information temporarily"""

    def __init__(self, dictionary, flushCount=10000):
        server = SemtracServer()
        cursor = server.get_db_cursor()
        self._db = cursor
        if flushCount > 0:
            self._flushCount = flushCount
        else:
            raise ValueError('flush count has to be greater than 0')
        self._data = list()
        self._count = 0
        self._dictionary = dictionary

        self._last_id = cache_queries.get_last_id_sets()
        if self._last_id is None:
            self._last_id = 0  # this is a protection against when the output db (sets) is empty.

    def _flush(self):
        """The function that coordinates the commit of the internal data store to the sql store."""
        # example:
        # (15, ([[('too', 0, 3), ('hot', 3, 6)], [('too', 0, 3), ('ott', 4, 7)]], 6))
        # print ("in _flush function")
        stage1 = self._genStage1()
        cache_queries.set_checks('0')
        cache_queries.insert_many_set(stage1)

        self._last_id = cache_queries.get_last_id_sets()

        stage2 = self._genStage2(self._last_id - len(stage1) + 1)
        cache_queries.insert_many_set_contains(stage2)
        cache_queries.set_checks('1')
        cache_queries.commit_db()
        self._data = list()
        self._count = 0

    def _genStage1(self):
        """Generates the package of data for the stage1 commit into the database."""
        stage1 = list()
        for result in self._data:
            pass_id = result[0]
            result = result[1][0]  # don't care about result length field.
            for rset in result:  # walks through the sets of results.
                stage1.append((pass_id, self._genSetPW(rset)))  # smooshes the results into a tuple.
        return stage1

    def _genStage2(self, startingID):
        """ Generates the package of data for stage2 commit into db."""
        # -- refresh dictionary (for dynamic entries)
        #        self._dictionary = reloadDynamicDictionary( self._db, self._dictionary)
        stage2 = []

        currID = startingID

        for result in self._data:
            result = result[1][0]
            for rset in result:  # rset is the list of fragments of a password
                for word, sIndex, eIndex in rset:
                    try:
                        stage2.append((currID, self._dictionary[word][1], sIndex, eIndex))
                    except KeyError, e:  # if key fragment not found in memory, go to db
                        try:
                            entry = cache_queries.get_dict_id_for_word(word)
                            stage2.append((currID, entry, sIndex, eIndex))
                        except:
                            print "Word {} not found in memory and db...".format(word)
                            print entry
                currID += 1

        return stage2

    def _genSetPW(self, tups):
        """Simply gets the password for the set from the list of words."""
        return ''.join([x[0] for x in tups])

    def addCommit(self, pwID, resultSet):
        """Adds data to the internal store to be flushed at a later time,
        when flushCount is exceeded, or object is deleted.
        Return True if this entry triggered flushing; False otherwise."""
        self._data.append((pwID, resultSet))
        self._count += 1
        if self._count > self._flushCount:
            self._flush()
            return True
        return False