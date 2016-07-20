import re
import time
from include.cache_data import TempClearTextWriteBuffer, Cache
import database.get_queries as get_queries
import database.post_queries as post_queries
import include.util as utils
from include.custom_exceptions import AllowedTimeExceededError

__author__ = 'Ameya'

cache = Cache()
NUM_DICT_ID = 200
MIXED_NUM_SC_DICT_ID = 201
SC_DICT_ID = 202
CHAR_DICT_ID = 203
MIXED_ALL_DICT_ID = 204


def segment_password(clear_text, check_mangling, participant_id):
    wbuff = TempClearTextWriteBuffer(100000)
    if len(clear_text) == 0:
        return
    if clear_text.strip(" ") == '':
        return

    # add Password to database temporarily.
    post_queries.insert_clear_password(participant_id, clear_text)
    pass_id = get_queries.get_last_insert_id()

    res = mine_word(clear_text, check_mangling)

    # store results
    if len(res) > 0:
        flush = wbuff.addCommit(pass_id, res)

    wbuff._flush()  # flush the rest


def tag_word_dictid(s):
    if utils.is_int(s):
        dyn_dict_id = NUM_DICT_ID
    elif utils.is_char_chunk(s):
        dyn_dict_id = CHAR_DICT_ID
    elif utils.is_sc_chunk(s):
        dyn_dict_id = SC_DICT_ID
    elif utils.is_num_sc_chunk(s):
        dyn_dict_id = MIXED_NUM_SC_DICT_ID
    else:
        dyn_dict_id = MIXED_ALL_DICT_ID
    return dyn_dict_id


def permute_string(word):
    """Takes a string, outputs a list of permutations of lengths in a list.
    Used by the miner to get strings it can look up in the hash tree
    (aka, python dict), as a speed improvement.
    """
    wordperm = list()
    for size in range(1, len(word) + 1):
        for pos in range(0, len(word) - size + 1):
            wordperm.append((word[pos:pos + size], pos, pos + size))
    return wordperm


def generate_all_list_permutations(mapping_dict):
    """This function takes input as a dictionary of lists and generates all possible mappings
    Mappings can be used to replace key with values
    Returns list of all possible mappings"""
    result_list = []
    max_list_length = get_maximum_list_length(mapping_dict)
    for i in mapping_dict:  # for each element in mapping_dict
        for j in range(0, len(mapping_dict[i])):  # for each element of list inside element of dict
            for n in range(0, max_list_length):  # to map j with each possible list element of other dict elements
                temp_map = {}
                for k in mapping_dict:
                    if k == i:
                        temp_map[k] = mapping_dict[k][j]
                    else:
                        if len(mapping_dict[k]) > n:  # not all elements of dict have same length lists
                            temp_map[k] = mapping_dict[k][n]
                        else:
                            temp_map[k] = mapping_dict[k][len(mapping_dict[k]) - 1]
                if temp_map not in result_list:
                    result_list.append(temp_map)

    return result_list


def get_re_replaced_string_list(match_str, mapping_dict):
    str_variation_list = []
    all_mappings_list = generate_all_list_permutations(mapping_dict)
    for i in range(0, len(all_mappings_list)):
        for m in all_mappings_list[i]:
            match_str = match_str.replace(m, all_mappings_list[i][m])
        str_variation_list.append(match_str)

    return str_variation_list


def order_sort_subs_list(subslist):
    """Expects a list of tuples conforming to (word, s_index, e_index)

    Sorts the list according to an order believed to produce the faster running
    of the algorithm.
    Sorts such that to select segments which start with s_index in ascending order first,
    but segments which are big lengthwise.
    For example, in password "anyoneelse", "anyone" will appear first and then "any" & "one".
    This is done so as to cover as lengthy segment as possible in the password
    """
    # sorts first by e_index, then sorts by s_index
    temp = sorted(subslist, key=lambda x: x[2], reverse=False)
    return sorted(temp, key=lambda x: x[1])


def eval_len(word_list):
    """Evaluates the total length of a list of words put in, in the standard processing format of this program."""
    totlen = 0
    for word in word_list:
        totlen += word[2] - word[1]
    return totlen


def possible_tail_strings(current_word, sub_list):
    """Takes e_index from the current word, and subList of the remaining words.

    Returns the a list of original tuples that are non-overlapping with the
    e_index of the current word.
    """
    out_list = list()
    for tup in sub_list:
        if tup[1] >= current_word[2]:
            out_list.append(tup)
    return out_list  # returns the start and end index of words and returns the tupple like 0,3,che


def ret_word_lists(x, current_word, rem_words):
    """Somehow returns a weird list/copy of the words list. don't know why i made it exactly."""
    tempCW = list()
    tempRW = list()
    for v in current_word:
        tempCW.append(v)
    for v in rem_words:
        tempRW.append(v)
    tempCW.append(x)
    tempRW.remove(x)
    tempRW = possible_tail_strings(tempCW[-1], tempRW)
    return (tempCW, tempRW)


def set_cover(current_word, rem_words, word_length, start_time):
    """Recursive algorithm to calculate the Set Cover for the words found in the password.
    Runs very slow for large numbers of input words.

    sTime -- pass the current time. If execution takes more than 60s, raises AllowedTimeExceededError
    """

    ALLOWED_TIME = 60  # in seconds
    if time.time() - start_time > ALLOWED_TIME:
        raise AllowedTimeExceededError("SetCover function exceeded {}s".format(ALLOWED_TIME))

    if len(rem_words) <= 1:
        if len(rem_words) is 1:
            current_word.append(rem_words[0])
        if len(current_word) is 1 and isinstance(current_word[0], str):
            return ([current_word], len(current_word))
        return (
            [current_word],
            eval_len(current_word))  # This returns current_word appended with 1 rem_words along with the actual
        # length of all segments.

    max_len_set = list()
    max_len = 0
    length = list()

    for x in rem_words:
        if (word_length - max_len) < (x[1] - current_word[-1][2]):
            break  # short circuit to stop trying once we can't make a sequence that beats maxLen

        tempW = ret_word_lists(x, current_word, rem_words)
        length = set_cover(tempW[0], tempW[1], word_length, start_time)

        if length[1] == max_len:
            for x in length[0]:
                if x not in max_len_set:
                    max_len_set.append(x)
        elif length[1] > max_len:
            max_len = length[1]
            max_len_set = list()  # empty the list.
            for x in length[0]:
                if x not in max_len_set:
                    max_len_set.append(x)

    return (max_len_set, max_len)


def generate_candidates(word_list, clear_text):
    """ Takes a list of (possibly overlapping) words in form of tuples (word, s_index, e_index)
        and returns a list of candidate segmentations plus the corresponding coverage.
        For example:
        password: 'anybodyelse'

        wordList: [('any',0,3), ('anybody',0,7), ('body', 3, 7), ('else', 7, 11)]

        returns: [  ([[('any',0,3),('body', 3, 7),('else', 7, 11)]], 11),
                    ([[('anybody',0,6),('else', 7, 11)]], 11),
                    ([[('body', 3, 7),('else', 7, 11)]], 8)... ]

        This list includes segmentations with varied coverage.
        Don't ask me why the candidates contain that redudant list...
    """
    sublist = order_sort_subs_list(word_list)
    if len(sublist) is 0:
        return sublist

    # sort by start index
    sorted_list = sorted(word_list, key=lambda x: x[1])
    candidates = list()
    for x in sorted_list:
        try:
            q = set_cover([x], possible_tail_strings(x, sublist), len(clear_text), time.time())
            # calculate maximum segment length and store in q tuple
            if q:
                max_len_segment = 0
                for partition in q[0]:
                    for segment in partition:
                        len_segment = int(segment[2] - segment[1])
                        if max_len_segment < len_segment:
                            max_len_segment = len_segment
                q += (max_len_segment,)
            candidates.append(q)
        except AllowedTimeExceededError, e:
            print str(e)
            print "SetCover failed for the following password: {}".format(clear_text)
            candidates = list()
            break

    return candidates


def get_freq(word):
    return cache.get_n_gram_freq(word)


def get_bigram_freq(word1, word2):
    key = ' '.join([word1, word2])
    return cache.get_n_gram_freq(key)


def get_trigram_freq (word1, word2, word3):
    key = ' '.join([word1, word2, word3])
    return cache.get_n_gram_freq(key)


def get_best_bigram_trigram_score_r(x, num_words, freq_info):
    # Returns probability score based on frequencies of existing bigrams/trigrams.
    # frequency info will be set by the calling function getWinningBigramTrigram...
    tempf = 0
    score = 0
    result = 0

    # Base cases: the word frequency is found in unigram, bigram, or trigram lists
    if num_words == 1:
        tempf = get_freq(x[0][0])
        # if word is not in COCA but it's in other dictionary set magic frequency value
        if tempf == 0 and cache.check_in_dictionary(x[0][0]):
            tempf = 1
        set_size = freq_info[0]

    elif num_words == 2:
        tempf = get_bigram_freq(x[0][0], x[1][0])
        set_size = freq_info[1]

    elif num_words == 3:
        tempf = get_trigram_freq(x[0][0], x[1][0], x[2][0])
        set_size = freq_info[2]

    if tempf > 0:
        result = num_words
        score = float(tempf) / float(set_size)

    # Recursive case: the word frequency was not found, and we have at least
    # one word to try out.
    if score == 0 and num_words >= 1:
        i = 1
        while i <= 3:
            scorei = float(0)
            resulti = 0
            tmpscore = float(0)
            tmpres = 0

            if num_words > i:
                (scorei, resulti) = get_best_bigram_trigram_score_r(x[0:i], i, freq_info)
                (tmpscore, tmpres) = get_best_bigram_trigram_score_r(x[i:num_words], num_words - i, freq_info)

                # calculate the combined probability scores.
                scorei = scorei * tmpscore
                resulti = resulti + tmpres

            # only update the score if this combination turned out to be better.
            if scorei > score:
                (score, result) = (scorei, resulti)
            i += 1

            # the result portion of this return value may not be necessary.
    return (score, result)


def get_bigram_trigram_winner(candidate_list):
    best_list = []
    if len(candidate_list) == 1:
        best_list = candidate_list
    else:
        highest_score = 0.0
        # db = connectToDb()
        score = float(0)

        for x in candidate_list:
            num_words = len(x[0][0])
            # note that score represents best frequency score by bigrams and trigrams
            freq_info = cache.get_freq_info()
            (score, result) = get_best_bigram_trigram_score_r(x[0][0], num_words, freq_info)

            if score > highest_score:
                highest_score = score
                best_list = [x]
            elif score == highest_score:
                best_list.append(x)

        if len(best_list) == 0:
            best_list = candidate_list
    return best_list


def get_max_freq(var):
    # this function finds the maximum frequency from a list of minimum frequency
    m = var[0]
    for x, y in var:
        if y > m[1]:
            m = x, y
    return m

def get_freq_based_winner(candidates_list):
    # tie-breaking based on frequency of word (tries to find the candidate
    # with the least odd word).
    list_freq = []
    min_freq = []
    k = 0

    if len(candidates_list) > 1:
        for x in candidates_list:
            for xword in x[0][0]:
                f = get_freq(xword[0])
                list_freq.append(f)
            min_freq.append((k, min(list_freq)))
            k += 1
            list_freq = []
        max_freq = get_max_freq(min_freq)
        best_list = candidates_list[max_freq[0]]
    elif len(candidates_list) == 1:
        best_list = candidates_list[0]

    return best_list


def best_candidate(candidates):
    """ Receives a list of candidate segmentations and selects the best
        based on the following criteria:
        1. Coverage
        2. Recursive n-gram scoring - product of frequencies of n-grams (trigram/bigram/unigram)
        3. Oddest single word - frequency of the least frequent word
    """

    if len(candidates) is 0:
        return candidates

    temp = list()
    # maxCoverage = 0
    max_length_segment_password = 0

    # First metric to select best result is coverage -- compile a list of the sets
    # that provide the best word-coverage.

    for x in candidates:
        if x[2] < max_length_segment_password:
            # the length of this one is shorter than what we already have.
            continue
        elif x[2] == max_length_segment_password:
            # it's the same max length
            temp.append(x)
        elif x[2] > max_length_segment_password:
            max_length_segment_password = x[2]
            # doesn't matter how many words we have, replace.
            temp = list()
            temp.append(x)
    # Next we overwrite candidates, reformatting the entries (so all wordList are in a consistent format)
    candidates = []
    for t in temp:
        for x in t[0]:
            """ Note: we're putting x in an array to maintain compatibility
            with database writing functions."""
            candidates.append(([x], t[1]))

    # Run the core tie-breaker. Try to get the best result based on
    # whether it exists in bigram/trigram lists.
    max_cover_list = get_bigram_trigram_winner(candidates)

    # finally, if we still have a tie, try to get the winning
    # result based on the oddest single word frequencies
    max_cover_list = get_freq_based_winner(max_cover_list)

    return max_cover_list


def add_gaps(ret_val, i, word, last_end_index, next_start_index):
    gap = word[last_end_index:next_start_index].strip()

    dyn_dict_id = tag_word_dictid(gap)
    new_len = ret_val[1]

    if len(gap) > 0 and dyn_dict_id> 0:
        post_queries.add_to_dynamic_dictionary(dyn_dict_id, gap)
        ret_val[0][0].insert(i, (gap, last_end_index, next_start_index))
        new_len += (next_start_index - last_end_index)

    return (ret_val[0], new_len)


def process_gaps(result_set, word):
    """ scrutinize result_set for sequence of numbers and special chars...
    if any exist, add them into the dictionary table as a new entry
    under dictset_id NUM_DICT_ID (for all numbers) and SC_DICT_ID (for all scs),
    and MIXED_NUM_SC_DICT_ID (for a block of mixed numbers and scs).
    Now we're also adding in garbage mixed everything under the id
    CHAR_DICT_ID

    We add these gaps into the resultSet, at the relevant position.
    """

    # New processing. Add pwd to dynamic dictionary as-is. No parsing.
    if result_set == []:
        result_set = ([[(word, 0, len(word))]], len(word))
        dyn_dict_id = tag_word_dictid(word)
        post_queries.add_to_dynamic_dictionary(dyn_dict_id, word)
    else:
        last_end_index = 0
        next_start_index = 0
        i = 0
        try:
            # iterates through the results. after the filtering by coverage
            # and frequency, there should be only one, though
            for result in result_set[0]:
                for x in result:
                    (xw, xs, xe) = x
                    next_start_index = xs
                    if next_start_index > last_end_index:
                        # find the gap, see if it is a #/sc chunk
                        result_set = add_gaps(result_set, i, word, last_end_index, next_start_index)
                    last_end_index = xe
                    i += 1
                if len(word) > last_end_index:
                    result_set = add_gaps(result_set, i, word, last_end_index, len(word))
        except:
            print ("Warning: caught unknown error in addTheGaps -- resultSet=", result_set, "password", word)

    return result_set


def mine_word(clear_text, check_mangling):
    """Breaks a password in pieces, which can be words (present in the dictionaries) or sequences of
       numbers, symbols and characters that do not constitute a word.
    """

    # classifies password
    dyn_dictionary_id = tag_word_dictid(clear_text)

    # if contains only numbers and/or symbols, or contains only one character,
    # insert it into the dyn. dictionary and don't try to parse
    if (dyn_dictionary_id != MIXED_ALL_DICT_ID and dyn_dictionary_id != CHAR_DICT_ID) \
            or (clear_text.strip(clear_text[0]) == ''):
        post_queries.add_to_dynamic_dictionary(dyn_dictionary_id, clear_text)
        # Just return the password as-is; there is no word to be found.
        result_set = ([[(clear_text, 0, len(clear_text))]], len(clear_text))

    # Otherwise, try to find the best word-parsing
    else:
        permutations = permute_string(clear_text.lower())
        words = list()
        for x in permutations:
            if cache.check_in_dictionary(x[0]):
                words.append(x)
            else:
                # check for special mappings
                SPECIAL_CHAR_MATCH = '[!1~@#3$5\|0487\+]'
                special_char_mapping = {
                    '!': ['i', 'l'],
                    '1': ['i', 'l'],
                    '~': ['s'],
                    '@': ['a'],
                    '#': ['h'],
                    '3': ['e'],
                    '$': ['s'],
                    '5': ['s'],
                    '|': ['i', 'l'],
                    '0': ['o'],
                    '4': ['a'],
                    '8': ['b'],
                    '7': ['l', 't'],
                    '+': ['t']
                }
                if re.search(SPECIAL_CHAR_MATCH, x[0]) is not None and check_mangling and len(x[0]) > 1:
                    if not x[0].isdigit():
                        replaced_string_list = get_re_replaced_string_list(x[0], special_char_mapping)
                        for string_index in range(0, len(replaced_string_list)):
                            if cache.check_in_dictionary(replaced_string_list[string_index]):
                                words.append((replaced_string_list[string_index], x[1], x[2]))
                                # Not sure whether to stop on encountering a valid word or insert all words
                                break

        candidates = generate_candidates(words, clear_text)
        result_set = best_candidate(candidates)

        # add the trashy fragments in the database
        result_set = process_gaps(result_set, clear_text)

    return result_set