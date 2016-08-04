import pos_tagger
from server import SemtracServer
import database.cache_queries as cache_queries

__author__ = 'Ameya'


class Cache():
    class __Cache():

        def __init__(self, db):
            server = SemtracServer()
            if db is None:
                db = server.get_db_conn()
            self.db_conn = db
            self.db_cursor = server.get_db_cursor()

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

        def get_dictionary(self):
            return self.dictionary

        def check_in_dictionary(self, word):
            return True if word in self.dictionary else False

        def get_n_gram_freq(self, word):
            return 0 if word not in self.ngrams else self.ngrams[word]

        def get_freq_info(self):
            return self.freq_info

        def pos_tag_words(self, words):
            return self.pos_tagger_data.tag(words)

    __instance = None

    def __init__(self, db=None):
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

    def __init__(self, flushCount=10000):
        if flushCount > 0:
            self._flushCount = flushCount
        else:
            raise ValueError('flush count has to be greater than 0')
        self._data = list()
        self._count = 0
        # Get dictionary from cache
        cache = Cache()
        self._dictionary = cache.get_dictionary()

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
        # self._dictionary = reloadDynamicDictionary( self._db, self._dictionary)
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


class TempWordBuffer():
    """ A few notes:

    - Caching is implemented for saving and reading.
    - The sample param in the constructor is important when planning to fetch only
      a sample. The MySQLDb docs mention: "you MUST retrieve the entire result set and
      close() the cursor before additional queries can be peformed on
      the connection."
      If you don't retrieve the entire result set before calling finish(), it will take
      forever to close the connection.

    """

    def __init__(self, pwset_id, save_cachesize=100000):

        self.savebuffer_size = save_cachesize
        self.readbuffer_size = 100000
        self.pwset_id = pwset_id

        self.readbuffer = []
        self.row = None  # holds the next row to be retrieved by nextPwd(),
        self.readpointer = -1  # always points to the last row read from readbuffer by fetchone.

        self.savebuffer = []

        # different connections for reading and saving
        self._init_read_cursor()

    def _init_read_cursor(self):
        # getting number of 'sets' (or segments)
        self.sets_size = cache_queries.get_sets_count_for_participant(self.pwset_id)

        # fetching the first password
        self.fill_buffer()
        self.row = self.fetchone()

    def fill_buffer(self):
        segments = cache_queries.get_word_segments(self.pwset_id, self.readbuffer_size)
        self.readbuffer = segments
        self.readpointer = -1

    def fetchone(self):
        try:
            self.readpointer += 1
            return self.readbuffer[self.readpointer]
        except:
            # print "Refilling buffer..."
            self.fill_buffer()
            if len(self.readbuffer) < 1:
                return None
            else:
                self.readpointer += 1
                return self.readbuffer[self.readpointer]

    def next_password(self):
        if self.row is None:
            return None

        pwd_id = old_pwd_id = self.row['set_id']
        pwd = []

        while pwd_id == old_pwd_id:
            f = Fragment(self.row["set_contains_id"], self.row["dictset_id"], self.row["dict_text"],
                         self.row["pos"], self.row["sentiment"], self.row["synset"],
                         self.row["category"], self.row["pass_text"], self.row["s_index"],
                         self.row["e_index"])
            pwd.append(f)

            self.row = self.fetchone()
            if self.row is None:
                break
            else:
                pwd_id = self.row['set_id']

        return pwd

    def save(self, wo, cache=False):
        if cache:
            self.savebuffer.append((wo.pos, wo.senti, wo.synsets, wo.id))
            if len(self.savebuffer) >= self.savebuffer_size:
                self.flush_save()
        else:
            cache_queries.update_set_contains((wo.pos, wo.senti, wo.synsets, wo.id))

    def flush_save(self):
        # print "updating {} records on the database...".format(len(self.savebuffer))
        cache_queries.update_set_contains(self.savebuffer)
        self.savebuffer = []

    def save_category(self, wo):
        cache_queries.update_set_category(wo.id, wo.category)

    def has_next(self):
        return self.row is not None

    def finish(self):
        if len(self.savebuffer) > 0:
            self.flush_save()


class Fragment():
    def __init__(self, ident, dictset_id, word, pos=None, senti=None,
                 synsets=None, category=None, password=None, s_index=None, e_index=None):
        self.id = ident
        self.dictset_id = dictset_id
        self.word = word
        self.pos = pos
        self.senti = senti
        self.synsets = synsets
        self.category = category
        self.password = password
        self.s_index = s_index
        self.e_index = e_index

    def __str__(self):
        return self.word

    def __repr__(self):
        return self.word

    def is_gap(self):
        return self.dictset_id > 90