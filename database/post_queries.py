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
