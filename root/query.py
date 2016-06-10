
names = "SELECT dict_text FROM dictionary where dictset_id = 20 or dictset_id = 30;"


def segments(pwset_id, limit, offset, pass_ids=None, exception=None):
    """ Returns all the segments.

    pwset_id - the id of the password set to be gathered
    bounds - list of the form [offset, size]
    pass_ids - list of password ids whose segments will be fetched.

    """

    q = "SELECT sets.set_id AS set_id, "\
        "set_contains.id AS set_contains_id, dict_text, dictset_id, "\
        "pos, sentiment, synset, category, dictset_id, pass_text, s_index, e_index "\
        "FROM passwords "\
        "JOIN sets on sets.pass_id = passwords.pass_id "\
        "JOIN set_contains ON set_contains.set_id = sets.set_id "\
        "JOIN dictionary ON set_contains.dict_id = dictionary.dict_id "\
        "WHERE passwords.pwset_id = {} ".format(pwset_id)

    if exception:
        q = q + "AND passwords.pass_id NOT IN {} ".format(tuple(exception))

    if pass_ids:
        q = q + "AND sets.pass_id in ({}) ".format(str(pass_ids)[1:-1])
    
    if limit:
        q = q + "LIMIT {} ".format(limit)
    if offset:
        q = q + "OFFSET {} ".format(offset)

    # print q
    return q


def n_sets(pwset_id):
    """ Retrieves the number of sets (segmentations) associated with a certain group
    of passwords.

    pwset_id - the id of the target group of passwords
    """

    return "SELECT COUNT(*) as count FROM sets LEFT JOIN passwords on sets.pass_id = passwords.pass_id " \
           "WHERE passwords.pwset_id = {}".format(pwset_id)


def extent_parsed(pwset_id):
    """ Returns the SQL string to query the minimum and maximum pass_id (that have been parsed)
        from a group of passwords (determined by pwset_id). If no passwords have been parsed
        from the group, this query will return empty.
    """
    return "SELECT MAX(pass_id) as max, MIN(pass_id) as min FROM sets LEFT JOIN passwords on sets.pass_id = passwords.pass_id " \
            "WHERE passwords.pwset_id = {}".format(pwset_id)


def extract_dictionary_word(dictset_id, seq_no):
    """
    :param dictset_id: Dictionary Set ID
    :param seq_no: The position corresponding to the dictionary set to be extracted
    :return: The corresponding query
    Description: Generates a query to extract dictionary word as per the position in the corresponding
                dictset_id
    """
    query = "SELECT dict_text FROM passwords.dictionary WHERE dictset_id = {} " . format(dictset_id)
    query += "LIMIT 1 OFFSET {}" . format(seq_no - 1)
    return query


def extract_wordlist_word(pos, seq_no):
    """
    Description: Generates a query to extract wordlist word as per the position in the corresponding
                pos
    """
    query = "SELECT wordlist_text FROM passwords.wordlist WHERE wordset_id = (SELECT wordset_id FROM passwords.wordlist_set " \
            "WHERE wordset_name = '{}') " . format(pos)
    query += "LIMIT 1 OFFSET {}" . format(seq_no - 1)
    return query


def count_dictionary_type(dictset_id):
    """
    Description: Returns query to count the number of words corresponding to the type of dictset_ids in dictionary
    """
    query = "SELECT COUNT(*) as count FROM passwords.dictionary WHERE dictset_id = {} " . format(dictset_id)
    return query


def count_wordlist_type(pos):
    """
    Description: Returns query to count the number of words corresponding to the type of POS in wordlist
    """
    query = "SELECT COUNT(*) as count FROM passwords.wordlist WHERE wordset_id = (SELECT wordset_id FROM passwords.wordlist_set " \
            "WHERE wordset_name = '{}') " . format(pos)
    return query


def get_wordset_id(pos):
    """
    Description: Returns query to return wordset_id if wordlist_set contains pos
    """
    query = "SELECT wordset_id FROM passwords.wordlist_set WHERE wordset_name = '{}'" . format(pos)
    return query


def get_grammar_id(grammar_text):
    """
    Description: Returns query to return grammar_id for grammar_text
    """
    query = "SELECT grammar_id FROM grammar WHERE grammar_text = '{}'".format(grammar_text)
    return query


def insert_grammar(grammar_text):
    """
    Description: Returns query to insert the grammar
    """
    query = "INSERT INTO grammar SET grammar_text = '{}'".format(grammar_text)
    return query

def save_transformed_password(transformed_cred_id, transformed_password, grammar_id):
    """
    Description: Returns query to update transformed_credentials table to store the corresponding transformed_password
    """
    query = "UPDATE transformed_credentials SET password_text = '{}', password_grammar_id = {} WHERE transformed_cred_id = {}".format \
        (transformed_password, grammar_id, transformed_cred_id)
    return query


def save_transformed_username(transformed_cred_id, transformed_username):
    """
    Description: Returns query to update transformed_credentials table to store the corresponding transformed_username
    """
    query = "UPDATE transformed_credentials SET username_text = '{}' WHERE transformed_cred_id = {}".format(transformed_username,
                                                                                                                   transformed_cred_id)
    return query


def save_transformed_segment_info(transformed_cred_id, transformed_segment, capitalization_info, special_char_info):
    """
    Description: Returns query to insert capitalization info for transformed_segment along with transformed_cred_id
    """
    query = "INSERT INTO transformed_segments SET transformed_cred_id = {}, segment = '{}', capital = '{}', special = '{}'".format \
        (transformed_cred_id, transformed_segment, capitalization_info, special_char_info)
    return query