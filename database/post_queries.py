from server import SemtracServer
import include.util as utils
import get_queries
from dateutil import parser

__author__ = 'Ameya'

server = SemtracServer()
db = server.get_db_conn()


def execute_commit_query(query):
    cursor = server.get_db_cursor()
    cursor.execute(query)
    cursor.close()
    db.commit()


def insert_participant_id(one_way_hash):
    query = "INSERT INTO password_set SET pwset_name='" + one_way_hash + "', max_pass_length=50"
    execute_commit_query(query)


def add_website(website_url):
    query = "INSERT INTO websites SET website_text = '{}'".format(website_url)
    execute_commit_query(query)


def insert_new_user_website(website_id, pwset_id):
    query = "INSERT INTO user_websites SET website_id = {}, pwset_id = {}".format(website_id, pwset_id)
    execute_commit_query(query)


def insert_transformed_cred_id(user_website_id, password_strength, password_warning):
    query = "INSERT INTO transformed_credentials SET user_website_id = {}, password_strength = {}, password_warning = '{}'"
    query = query.format(user_website_id, float(password_strength), utils.escape(password_warning))
    execute_commit_query(query)


def insert_clear_password(pwset_id, clear_password):
    query = "INSERT INTO passwords SET pwset_id = {}, pass_text = '{}'".format(pwset_id, utils.escape(clear_password))
    execute_commit_query(query)


def add_to_dynamic_dictionary(dyn_dict_id, segment):
    # right-strip it cause MySQL doesn't consider trailing spaces
    segment = segment.rstrip()

    query = '''INSERT INTO dictionary (dictset_id, dict_text)
    SELECT * FROM (SELECT ''' + str(dyn_dict_id) + ''' AS id,  \'''' + utils.escape(segment) + '''\' AS text  )
    AS tmp WHERE NOT exists (SELECT dictset_id, dict_text FROM dictionary WHERE
    dictset_id = ''' + str(dyn_dict_id) + ''' AND dict_text = "''' + str(segment) + '''");'''
    execute_commit_query(query)


def insert_password_key(pwset_id, password_key):
    query = "UPDATE password_set SET password_key='{}' WHERE pwset_id={}".format(password_key, pwset_id)
    execute_commit_query(query)


def save_transformed_segment_info(transformed_cred_id, transformed_segment, capitalization_info, special_char_info):
    query = "INSERT INTO transformed_segments SET transformed_cred_id = {}, segment = '{}', capital = '{}', special = '{}'".format \
        (transformed_cred_id, utils.escape(transformed_segment), capitalization_info, special_char_info)
    execute_commit_query(query)


def save_transformed_username(transformed_cred_id, transformed_username):
    query = "UPDATE transformed_credentials SET username_text = '{}' WHERE transformed_cred_id = {}".format(
        utils.escape(transformed_username),
        transformed_cred_id)
    execute_commit_query(query)


def insert_grammar(grammar_text):
    query = "INSERT INTO grammar SET grammar_text = '{}'".format(grammar_text)
    execute_commit_query(query)


def save_transformed_password(transformed_cred_id, transformed_password, grammar_text):
    # Get grammar_id
    grammar_id = get_queries.get_grammar_id(grammar_text)
    query = "UPDATE transformed_credentials SET password_text = '{}', password_grammar_id = {} WHERE transformed_cred_id = {}".format \
        (utils.escape(transformed_password), grammar_id, transformed_cred_id)
    execute_commit_query(query)


def clear_plain_text_data():
    query = "DELETE FROM passwords.passwords"
    execute_commit_query(query)
    query = "DELETE FROM sets"
    execute_commit_query(query)
    query = "DELETE FROM set_contains"
    execute_commit_query(query)


def append_email_domain_username(transformed_cred_id, email_domain):
    old_username = get_queries.get_transformed_username(transformed_cred_id)
    if old_username is not None:
        # append email_domain to old_username
        new_username = old_username + str(email_domain)
        query = "UPDATE transformed_credentials SET username_text = '{}' WHERE transformed_cred_id={}".format(
            utils.escape(new_username), transformed_cred_id)
        execute_commit_query(query)


def clear_password_key():
    query = "UPDATE password_set SET password_key = NULL"
    execute_commit_query(query)


def save_auth_status(transformed_cred_id, status):
    query = "UPDATE transformed_credentials SET auth_status = {} WHERE transformed_cred_id = {}".format(status,
                                                                                                        transformed_cred_id)
    execute_commit_query(query)


def insert_prestudy_answers(participant_id, answers):
    for answer in answers:
        if 0 < answer['answer'] < 6:
            query = "DELETE FROM study_responses WHERE pwset_id = {} AND question_id = {}".format(participant_id,
                                                                                                  answer['question_id'])
            execute_commit_query(query)
            query = "INSERT INTO study_responses SET pwset_id = {}, question_id = {}, response_obj = {}".format(
                participant_id, answer['question_id'], answer['answer'])
            execute_commit_query(query)
        else:
            return None

    return 1


def insert_poststudy_answers(participant_id, answers):
    for answer in answers:
        if 0 < answer['answer'] < 6:
            query = "DELETE FROM study_responses WHERE pwset_id = {} AND question_id = {} AND website_id = {}".format(
                participant_id, answer['question_id'], answer['website_id'])
            execute_commit_query(query)
            query = "INSERT INTO study_responses SET pwset_id = {}, question_id = {}, website_id = {}, response_obj = {}".format(
                participant_id, answer['question_id'], answer['website_id'], answer['answer'])
            execute_commit_query(query)
        else:
            return None

    return 1


def insert_user_website(participant_id, website_id, user_probability, reset_count, date_time_obj):
    query = "INSERT INTO user_websites SET pwset_id = {}, website_id = {}, website_probability={}, password_reset_count = {}, date = '{}'".format(
        participant_id, website_id, user_probability, reset_count, date_time_obj)
    execute_commit_query(query)


def insert_website_list(participant_id, website_list):
    new_website_id_list = ()
    for website in website_list:
        try:
            url = website['url']
            website_id = get_queries.check_website_exists(url)

            if website_id is None:
                # add the website and fetch website_id
                add_website(url)
                website_id = get_queries.check_website_exists(url)

            new_website_id_list += (int(website_id),)
            # Now, we have website_id
            # Convert date time string to datetime object
            # dateTimeFormat = '%a, %d %b %Y %H:%M:%S %z'
            null_date_flag = False
            if str(website['date']) is "":
                null_date_flag = True
            else:
                try:
                    date_time_obj = parser.parse(website['date'], ignoretz=True)
                except ValueError:
                    print "date exception"
                    date_time_obj = parser.parse(website['date'].split("(")[0], ignoretz=True)

            website_user_probability = 1 if website['important'] else 0

            # First check if entry exists in transformed_passwords table, update it else insert new entry
            user_website_id = get_queries.get_user_website_id(participant_id, website_id)
            if user_website_id is not None:
                if null_date_flag:
                    query = "UPDATE user_websites SET website_probability = {}, password_reset_count = {} WHERE user_website_id = {}".format(
                        website_user_probability, website['reset_count'], user_website_id)
                    execute_commit_query(query)
                else:
                    query = "UPDATE user_websites SET website_probability = {}, password_reset_count = {}, date = '{}' WHERE user_website_id = {}".format(
                        website_user_probability, website['reset_count'], date_time_obj, user_website_id)
                    execute_commit_query(query)
            else:
                insert_user_website(participant_id, website_id, website_user_probability, website['reset_count'],
                                    date_time_obj)
        except Exception as e:
            print e
            print "exception"
            continue

    # Now remove the websites present in database, but not in newly received website_list and websites which dont have
    # any password associated with them
    if len(new_website_id_list) == 1:
        # to remove the trailing comma
        website_id_list_str = "(" + str(new_website_id_list[0]) + ")"
    else:
        website_id_list_str = str(new_website_id_list)
    website_ids = get_queries.get_distinct_user_website_ids()
    not_user_website_ids = ()
    if len(website_ids) == 1:
        # to remove the trailing comma
        not_user_website_ids = "(" + str(int(website_ids[0]['user_website_id'])) + ")"
    else:
        for id in website_ids:
            not_user_website_ids += (int(id['user_website_id']),)
    if len(new_website_id_list) == 0:
        if len(website_ids) == 0:
            query = "DELETE FROM user_websites WHERE pwset_id = {}".format(participant_id)
        else:
            query = "DELETE FROM user_websites WHERE pwset_id = {} AND user_website_id NOT IN {}".format(participant_id,
                                                                                                         str(
                                                                                                             not_user_website_ids))
    elif len(website_ids) == 0:
        query = '''DELETE FROM user_websites WHERE pwset_id = {} AND website_id NOT IN {}'''.format(participant_id,
                                                                                                    website_id_list_str)
    else:
        query = '''DELETE FROM user_websites WHERE pwset_id = {} AND website_id NOT IN {} AND user_website_id NOT IN {}'''.format(
            participant_id, website_id_list_str, str(not_user_website_ids))
    execute_commit_query(query)


def add_new_website(participant_id, website_url, website_importance):
    website_id = get_queries.check_website_exists(website_url)
    if website_id is None:
        # add the website and fetch website_id
        add_website(website_url)
        website_id = get_queries.check_website_exists(website_url)
    user_website_id = get_queries.get_user_website_id(participant_id, website_id)
    if user_website_id is not None:
        query = "UPDATE user_websites SET website_probability = {} WHERE user_website_id = {}".format(
            int(website_importance), int(user_website_id))
        execute_commit_query(query)
        return 1
    query = "INSERT INTO user_websites SET pwset_id = {}, website_id = {}, website_probability = {}".format(
        participant_id, website_id, website_importance)
    execute_commit_query(query)
    return 1