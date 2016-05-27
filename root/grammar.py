#!/usr/bin/env python

"""
This script generates a context-free grammar
that captures the semantic patterns of a list of
passwords.

It's based on Weir (2009)*.

*http://dl.acm.org/citation.cfm?id=1608146

Created on Apr 18, 2013

"""
from database import Fragment

__author__ = 'rafa'

import database
import semantics
from cut import wagner
import sys
import traceback
from nltk.probability import FreqDist, ConditionalFreqDist
from timer import Timer
import re
import argparse
import shutil
import os
import md5
import string
import random

# -----------------------------------------
# Initializing module variables
#-----------------------------------------

nouns_tree = None
verbs_tree = None
node_index = None


def select_treecut(pwset_id, abstraction_level):
    """ Load the noun and verb trees and calculates the their respective tree 
    cuts.  Stores  them in the module  variables, nouns_tree, verbs_tree  and
    node_index.  node_index points to the nodes in the tree.
    """

    nouns_tree, verbs_tree = semantics.load_semantictrees(pwset_id)

    cut = wagner.findcut(nouns_tree, abstraction_level)
    for c in cut: c.cut = True

    cut = wagner.findcut(verbs_tree, abstraction_level)
    for c in cut: c.cut = True

    flat = nouns_tree.flat() + verbs_tree.flat()

    node_index = dict()
    for node in flat:
        if node.key not in node_index:
            node_index[node.key] = node

        #-------------------------------------------


class DictionaryTag:
    map = {10: 'month',
           20: 'fname',
           30: 'mname',
           40: 'surname',
           50: 'country',
           60: 'city',
           200: 'number',
           201: 'num+special',
           202: 'special',
           203: 'char',
           204: 'all_mixed'}

    # pos_map is used to map infrequent POS words to their respective parent class
    pos_map = {
        'prep': ['io', 'if', 'bcl', 'p'],
        'pn': ['ppis1', 'pphs2', 'ppis2', 'pnqs', 'ppio1', 'ppho2', 'ppho1', 'ppio2', 'ppx2', 'pnqo', 'ppge', 'pnqv',
               'pnx1'],
        'cc': ['c', 'ccb', 'csa', 'csn', 'cst', 'csw'],
        'dd': ['d', 'da', 'da1', 'da2', 'dar', 'dat', 'db2', 'dd1', 'dd2', 'ddqge', 'ddqv'],
        'vv0': ['vb0', 'vbdr', 'vbg', 'vbi', 'vbm', 'vbn', 'vbr', 'vd', 'vd0', 'vdd', 'vdg', 'vdi', 'vdn', 'vdz', 'vh0',
                'vhd',
                'vhg', 'vhi', 'vhn', 'vhz', 'vm', 'vmk', 'vvgk', 'vvnk'],
        'rr': ['ra', 'rex', 'rg', 'rgq', 'rgqv', 'rgr', 'rgt', 'rl', 'rpk', 'rrq', 'rrqv', 'rrr', 'rrt', 'rt', 'rp'],
        'mc': ['mc1', 'm', 'm1'],
        'jj': ['jk', 'j'],
        'nn': ['n', 'nna', 'nnl1', 'nnl2', 'nnt1', 'nnt2'],
        'nno': ['nno2'],
        'np': ['npd2'],
        'npm1': ['npm2']
    }

    _gaps = None

    @classmethod
    def get(cls, id):
        return DictionaryTag.map[id] if id in DictionaryTag.map else None

    @classmethod
    def gaps(cls):
        if not DictionaryTag._gaps:
            DictionaryTag._gaps = [v for k, v in DictionaryTag.map.items() if DictionaryTag.is_gap(k)]

        return DictionaryTag._gaps

    @classmethod
    def is_gap(cls, id):
        return id > 90


def generate_n_digit_random(n):
    range_start = 10 ** (n - 1)
    range_end = (10 ** n) - 1
    return random.randint(range_start, range_end)


def generate_n_char_random(n):
    return ''.join(random.choice(string.lowercase) for i in range(n))


def generate_n_symbol_random(n):
    return ''.join(random.choice(string.punctuation) for i in range(n))


def generalize(synset):
    """ Generalizes a synset based on a tree cut. """

    if synset.pos not in ['v', 'n']:
        return None

    # an internal node is split into a node representing the class and other
    # representing the sense. The former's name starts with 's.'
    key = synset.name if is_leaf(synset) else 's.' + synset.name

    try:
        node = node_index[key]
    except KeyError:
        sys.stderr.write("{} could not be generalized".format(key))
        return None

    path = node.path()

    # given the hypernym path of a synset, selects the node that belongs to the cut
    for parent in path:
        if parent.cut:
            return parent.key


def is_leaf(synset):
    return not bool(synset.hyponyms())


def refine_gap(segment):
    return DictionaryTag.map[segment.dictset_id] + str(len(segment.word))


def classify_by_pos(segment):
    """ Classifies  the  segment into number, word, character  sequence or
    special  character sequence.  Includes a POS tag if possible. Does not 
    include a semantic symbol/tag.
    If segment is a word, the tag consists in its POS tag. For numbers and 
    character sequences, a tag of the form categoryN is  retrieved where N 
    is  the length  of the segment.  Words with unknown pos  are tagged as 
    'unkwn'.
    Examples:
        love    -> vb
        123     -> number3
        audh    -> char4
        kripton -> unkwn
        !!!     -> special3
    """

    if DictionaryTag.is_gap(segment.dictset_id):
        tag = refine_gap(segment)
    else:
        tag = segment.pos if segment.pos else 'unkwn'

    return tag


def classify_pos_semantic(segment):
    """ Fully classify the segment. Returns a tag  possibly containing semantic
    and  syntactic (part-of-speech) symbols.  If the segment  is a proper noun,
    returns either month, fname, mname, surname, city or country,  as suitable.
    For  other words, returns a  tag of  the form pos_synset,  where  pos is  a
    part-of-speech tag and  synset is the corresponding  WordNet synset.  If no 
    synset exists, the symbol 'None' is used.   Aside from these classes, there 
    is also numberN, charN, and specialN, for numbers, character sequences  and 
    sequences of  special characters,  respectively, where N denotes the length
    of the segment.
    Examples:
        loved -> vvd_s.love.v.01
        paris -> city
        jonas -> mname
        cindy -> fname
        aaaaa -> char5
    """
    if DictionaryTag.is_gap(segment.dictset_id):
        tag = refine_gap(segment)
    elif segment.pos in ['np', 'np1', 'np2', None] and segment.dictset_id in DictionaryTag.map:
        tag = DictionaryTag.map[segment.dictset_id]
    else:
        # We dont have to use WordNet for USC Cloudsweeper.
        # So, no need to convert to Wordnet synset
        # just set the tag to segment.pos
        tag = segment.pos
        """
        synset = semantics.synset(segment.word, segment.pos)
        # only tries to generalize verbs and nouns
        if synset is not None and synset.pos in ['v', 'n']:
            # TODO: sometimes generalize is returning None. #fixit 
            tag = '{}_{}'.format(segment.pos, generalize(synset)) 
        else:
            tag = segment.pos
        """

    return tag


def classify_semantic_backoff_pos(segment):
    """ Returns a tag containing either a semantic or a syntactic (part-of-speech)
    symbol.  If the segment is a proper noun, returns either month, fname, mname,
    surname, city or country,  as suitable.
    For  other words, returns a semantic tag if the word is found in Wordnet,
    otherwise, falls back to a POS tag. Aside from these classes, there 
    is also numberN, charN, and specialN, for numbers, character sequences  and 
    sequences of  special characters,  respectively, where N denotes the length
    of the segment.
    Examples:
        loved -> s.love.v.01
        paris -> city
        jonas -> mname
        cindy -> fname
        aaaaa -> char5
    """
    if DictionaryTag.is_gap(segment.dictset_id):
        tag = refine_gap(segment)
    elif segment.pos in ['np', 'np1', 'np2', None] and segment.dictset_id in DictionaryTag.map:
        tag = DictionaryTag.map[segment.dictset_id]
    else:
        synset = semantics.synset(segment.word, segment.pos)
        # only tries to generalize verbs and nouns
        if synset is not None and synset.pos in ['v', 'n']:
            # TODO: sometimes generalize is returning None. #fixit 
            tag = generalize(synset)
        else:
            tag = segment.pos

    return tag


def classify_word(segment):
    """ Most basic form of classification. Groups strings with respect to their
    length and nature (number, word, alphabetic characters, special characters).
    Examples:
        loved -> word5
        lovedparisxoxo -> word5word5char4
        12345 -> number5
        %$^$% -> special5
    """
    word = segment.word
    length = len(word)

    if DictionaryTag.is_gap(segment.dictset_id):
        return refine_gap(segment)

    # if re.match(r'\d+', word):
    #     return 'number' + str(length)
    # elif re.match(r'[^a-zA-Z0-9]+', word):
    #     return 'special' + str(length)
    else:
        return 'word' + str(length)


def stringify_pattern(tags):
    return ''.join(['({})'.format(tag) for tag in tags])


def pattern(segments):
    return stringify_pattern([classify(s) for s in segments])


def sample(db):
    """ I wrote this function to output data for a table
    that shows words, the corresponding synsets, and their generalizations."""

    while db.hasNext():
        segments = db.nextPwd()
        for s in segments:
            tag = classify(s)
            if re.findall(r'.+\..+\..+', tag):  # test if it's a synset
                synset = semantics.synset(s.word, s.pos)
            else:
                synset = None
            print "{}\t{}\t{}\t{}".format(s.password, s.word, tag, synset)


def expand_gaps(segments):
    """
    If the password has segments of the type "MIXED_ALL" or "MIXED_NUM_SC",
    break them into "alpha", "digit" and "symbol" segments.
    This function provides more resolution in the treatment of non-word segments.
    This should be done in the parsing phase, so this is more of a quick fix.
    """
    temp = []

    for s in segments:
        if s.dictset_id == 204 or s.dictset_id == 201:
            temp += segment_gaps(s.word)
        else:
            temp.append(s)

    return temp


def segment_gaps(pwd):
    """
    Segments a string into alpha, digit and "symbol" fragments.
    """
    regex = r'\d+|[a-zA-Z]+|[^a-zA-Z0-9]+'
    segments = re.findall(regex, pwd)
    segmented = []
    for s in segments:
        if s[0].isalpha():
            f = Fragment(0, 203, s)
        elif s[0].isdigit():
            f = Fragment(0, 200, s)
        else:
            f = Fragment(0, 202, s)

        segmented.append(f)

    return segmented


def print_result(password, segments, tags, pattern):
    for i in range(len(segments)):
        print "{}\t{}\t{}\t{}".format(password, segments[i].word, tags[i], pattern)


def get_parent_pos(pos):
    if pos is None:
        return pos
    for parent_pos in DictionaryTag.pos_map:
        if pos.lower() in DictionaryTag.pos_map[parent_pos]:
            return parent_pos
    return pos


def generate_transformed_segment(segment, tag):
    # tag is generated by grammar classification
    one_way_hash = md5.new(segment.word).hexdigest()

    # Remove alphabets from MD5 hash
    string_translation = string.maketrans('', '')
    no_digits = string_translation.translate(string_translation, string.digits)
    one_way_hash = one_way_hash.translate(string_translation, no_digits)

    if segment.dictset_id <= 60:
        # map the hash to a position in database and return the word at that position
        total_dictionary_type = database.get_dictionary_type_count(segment.dictset_id)
        dictionary_position = int(one_way_hash) % int(total_dictionary_type)
        return database.get_dictionary_word(segment.dictset_id, int(dictionary_position))
    else:
        parent_pos = get_parent_pos(segment.pos)
        # Check if POS is in wordset
        if database.check_wordset_pos(parent_pos) and parent_pos is not None:
            total_wordlist_type = database.get_wordlist_type_count(parent_pos)
            wordlist_position = int(one_way_hash) % int(total_wordlist_type)
            if wordlist_position == 0:
                wordlist_position = 1  # In query, we subtract this number by 1. So, if this number is 1,
                # then the position will be 0 in query
            return database.get_wordlist_word(parent_pos, wordlist_position)
        else:
            # either a number, garbled characters or special symbols
            # check tag
            if "number" in tag:
                count = int(tag.split("number")[1])
                return generate_n_digit_random(count)
            elif "char" in tag:
                count = int(tag.split("char")[1])
                return generate_n_char_random(count)
            elif "special" in tag:
                count = int(tag.split("special")[1])
                return generate_n_symbol_random(count)
            else:
                print segment.word
                print tag
                return segment.word


def main(db, transformed_password_id, pwset_id, dryrun, verbose, basepath, tag_type):
    #    tags_file = open('grammar/debug.txt', 'w+')

    # print "Grammar Generation Starting..."
    patterns_dist = FreqDist()  # distribution of patterns
    segments_dist = ConditionalFreqDist()  # distribution of segments, grouped by semantic tag

    counter = 0

    while db.hasNext():
        segments = db.nextPwd()
        password = ''.join([s.word for s in segments])
        tags = []
        transformedPassword = ""

        segments = expand_gaps(segments)

        for s in segments:  # semantic tags
            if tag_type == 'pos':
                tag = classify_by_pos(s)
            elif tag_type == 'backoff':
                tag = classify_semantic_backoff_pos(s)
            elif tag_type == 'word':
                tag = classify_word(s)
            else:
                tag = classify_pos_semantic(s)

            tags.append(tag)
            transformedPassword += str(generate_transformed_segment(s, tag))
            segments_dist[tag][s.word] += 1

        pattern = stringify_pattern(tags)
        patterns_dist[pattern] += 1

        # Save transformed password in the database if transformed_password_id is not None
        database.save_transformed_password(transformed_password_id, transformedPassword, str(pattern))

        # outputs the classification results for debugging purposes
        if verbose:
            print_result(password, segments, tags, pattern)

        counter += 1
        if counter % 100000 == 0:
            print "{} passwords processed so far ({:.2%})... ".format(counter, float(counter) / db.sets_size)

        #     tags_file.close()

    pwset_id = str(pwset_id)

    if dryrun:
        return

    """
    # remove previous grammar
    try:
        shutil.rmtree(basepath)
    except OSError:  # in case the above folder does not exist
        pass

    # recreate the folders empty
    os.makedirs(os.path.join(basepath, 'nonterminals'))

    with open(os.path.join(basepath, 'rules.txt'), 'w+') as f:
        total = patterns_dist.N()
        for pattern, freq in patterns_dist.items():
            f.write('{}\t{}\n'.format(pattern, float(freq) / total))
        f.close()

    for tag in segments_dist.keys():
        total = segments_dist[tag].N()
        with open(os.path.join(basepath, 'nonterminals', str(tag) + '.txt'), 'w+') as f:
            for k, v in segments_dist[tag].items():
                f.write("{}\t{}\n".format(k, float(v) / total))
            f.close()
    """


def options():
    parser = argparse.ArgumentParser()

    parser.add_argument('password_set', default=1, type=int, \
                        help='The id of the collection of passwords to be processed')
    parser.add_argument('-s', '--sample', default=None, type=int, \
                        help="Sample size")
    parser.add_argument('-d', '--dryrun', action='store_true', \
                        help="Does not override the grammar folder. ")
    parser.add_argument('-v', '--verbose', action='store_true', \
                        help="Verbose mode")
    parser.add_argument('-e', '--exceptions', type=argparse.FileType('r'), \
                        help="A file containing a list of password ids \
        to be ignored. One id per line. Depending on the size of this file \
        you might need to increase MySQL's variable max_allowed_packet.")
    # parser.add_argument('--onlypos', action='store_true', \
    #     help="Turn this switch if you want the grammar to have only "\
    #     "POS symbols, no semantic tags (synsets)")
    parser.add_argument('-a', '--abstraction', type=int, default=5000, \
                        help='Abstraction Level. An integer > 0, correspoding to the ' \
                             'weighting factor in Wagner\'s formula')
    parser.add_argument('-p', '--path', default='grammar', \
                        help="Path where the grammar files will be output")
    parser.add_argument('--tags', default='pos_semantic', \
                        choices=['pos_semantic', 'pos', 'backoff', 'word'])

    return parser.parse_args()


# TODO: Option for online version (calculation of everything on the fly) and from db
if __name__ == '__main__':
    opts = options()

    exceptions = []

    if opts.exceptions:
        for l in opts.exceptions:
            exceptions.append(int(l.strip()))
        opts.exceptions.close()

    # Generalization of POS not required for USC Cloudsweeper. Using CLAWS7 tagset
    # if not opts.tags == 'pos':
    #     select_treecut(opts.password_set, opts.abstraction)

    try:
        with Timer('grammar generation'):
            #db = PwdDb(sample=10000, random=True)
            print 'Instantiating database...'
            db = database.PwdDb(opts.password_set, sample=opts.sample, exceptions=exceptions)
            try:
                main(db, None, opts.password_set, opts.dryrun, \
                     opts.verbose, opts.path, opts.tags)
            except KeyboardInterrupt:
                db.finish()
                raise
    except:
        e = sys.exc_info()[0]
        traceback.print_exc()
        sys.exit(1)
