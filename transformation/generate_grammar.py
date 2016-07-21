from nltk.probability import FreqDist, ConditionalFreqDist
from include.cache_data import TempWordBuffer
import database.get_queries as get_queries

__author__ = 'Ameya'


def generate_grammar(participant_id):
    word_buffer_obj = TempWordBuffer(participant_id)
    patterns_dist = FreqDist()  # distribution of patterns
    segments_dist = ConditionalFreqDist()  # distribution of segments, grouped by semantic tag

    # check for password_key, insert if necessary
    password_key = get_queries.get_password_key(participant_id)

    counter = 0

    while word_buffer_obj.has_next():
        segments = word_buffer_obj.next_password()
        password = ''.join([s.word for s in segments])
        tags = []
        transformed_password = ""

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
            transformedSegment = str(generate_transformed_segment(s, tag, password_key))
            transformedPassword += transformedSegment

            # Save transformed segment with corresponding capitalization information
            if kwargs.get("clearPassword") is not None:
                save_transformed_segment_info(transformed_cred_id, transformedSegment, tag, s.s_index, s.e_index,
                                              kwargs.get("clearPassword"))

            segments_dist[tag][s.word] += 1

        pattern = stringify_pattern(tags)
        patterns_dist[pattern] += 1

        if kwargs.get("type") == "username":
            # save username at transformed_cred_id and return
            # variable transformedPassword is actually transformed username
            transformedUsername = transformedPassword
            database.save_transformed_username(transformed_cred_id, transformedUsername)
            return

        # Save transformed password in the database if transformed_cred_id is not None
        if transformed_cred_id is not None:
            database.save_transformed_password(transformed_cred_id, transformedPassword, str(pattern))

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