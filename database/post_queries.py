from server import SemtracServer
import include.util as utils

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
    select * from (select ''' + str(dyn_dict_id) + ''' as id,  \'''' + utils.escape(segment) + '''\' as text  )
    as tmp where not exists (select dictset_id, dict_text from dictionary where
    dictset_id = ''' + str(dyn_dict_id) + ''' and dict_text = "''' + str(segment) + '''");'''
    execute_commit_query(query)