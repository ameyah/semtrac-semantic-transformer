from nltk.tag.sequential import DefaultTagger, BigramTagger, TrigramTagger, \
    SequentialBackoffTagger
from nltk.probability import FreqDist
from taggers import COCATagger, NamesTagger, WordNetTagger
import cPickle as pickle


class BackoffTagger(SequentialBackoffTagger):
    def __init__(self, pickle_path, coca_tagger_path, *args, **kwargs):
        SequentialBackoffTagger.__init__(self, *args, **kwargs)
        self.dist = FreqDist()
        train_sents = pickle.load(open(pickle_path))
        # make sure all tuples are in the required format: (TAG, word)
        train_sents = [[t for t in sentence if len(t) == 2] for sentence in train_sents]
        default_tagger = DefaultTagger('nn')
        wn_tagger = WordNetTagger(default_tagger)
        names_tagger = NamesTagger(wn_tagger)
        coca_tagger = COCATagger(names_tagger)
        coca_tagger.readCOCAList(coca_tagger_path)
        bigram_tagger = BigramTagger(train_sents, backoff=coca_tagger)
        trigram_tagger = TrigramTagger(train_sents, backoff=bigram_tagger)

        # doesn't include self cause it's a dumb tagger (would always return None)
        self._taggers = trigram_tagger._taggers

    def tag_one(self, tokens, index, history):
        tag = None
        for tagger in self._taggers:
            tag = tagger.choose_tag(tokens, index, history)
            if tag is not None:
                self.dist[tagger.__class__.__name__] += 1
                break
        return tag