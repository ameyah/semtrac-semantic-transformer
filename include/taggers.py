from nltk.tag import NgramTagger, SequentialBackoffTagger
from nltk.corpus import wordnet, names
from nltk.probability import FreqDist
import csv
import database.get_queries as queries


class WordNetTagger(SequentialBackoffTagger):
    """
    >>> wt = WordNetTagger()
    >>> wt.tag(['food', 'is', 'great'])
    [('food', 'nn'), ('is', 'vv0'), ('great', 'jj')]
    """

    def __init__(self, *args, **kwargs):
        SequentialBackoffTagger.__init__(self, *args, **kwargs)

        # maps wordnet tags to claws7 tags
        self.wordnet_tag_map = {
            'n': 'nn',
            's': 'jj',
            'a': 'jj',
            'r': 'rr',
            'v': 'vv0'
        }

    def choose_tag(self, tokens, index, history):
        word = tokens[index]
        if word is None:
            return None
        fd = FreqDist()

        for synset in wordnet.synsets(word):
            fd[synset.pos] += 1
        try:
            return self.wordnet_tag_map.get(fd.max())
        except:  # in case fd is empty
            return None


class NamesTagger(SequentialBackoffTagger):
    """
        >>> nt = NamesTagger()
        >>> nt.tag(['Jacob'])
        [('Jacob', 'np')]
    """

    def __init__(self, *args, **kwargs):
        SequentialBackoffTagger.__init__(self, *args, **kwargs)
        self.name_set = set(queries.get_names_dictionary())

    def choose_tag(self, tokens, index, history):

        word = tokens[index]

        if word is None:
            return None

        if word.lower() in self.name_set:
            return 'np'
        else:
            return None


class COCATagger(SequentialBackoffTagger):
    def __init__(self, *args, **kwargs):
        SequentialBackoffTagger.__init__(self, *args, **kwargs)

    def readCOCAList(self, COCAPath):
        coca_list = csv.reader(open(COCAPath), delimiter='\t')
        self.tag_map = dict()
        for row in coca_list:
            freq = int(row[0])
            word = row[1].strip()
            pos = row[2].strip()
            self.insertPair(word, pos, freq)

    def insertPair(self, word, pos, freq):
        """ Appends a (pos,freq) tuple in the end of the list
        corresponding to a word. Since they're ranked in coca file
        it should result in an ordered list by frequency """
        map_ = self.tag_map
        if (word not in map_):
            map_[word] = [(pos, freq)]
        else:
            map_[word].append((pos, freq))

    def choose_tag(self, tokens, index, history):
        word = tokens[index]
        if word in self.tag_map:
            posfreq = self.tag_map[word][0]
            # return self.tag_converter.claws7ToBrown(posfreq[0])
            return posfreq[0]
        else:
            return None