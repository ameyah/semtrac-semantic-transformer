from server import SemtracServer
import include.util as utils
import get_queries

__author__ = 'Ameya'

server = SemtracServer()
db = server.get_db_conn()
cursor = server.get_db_cursor()


def execute_commit_query(query):
    cursor.execute(query)
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