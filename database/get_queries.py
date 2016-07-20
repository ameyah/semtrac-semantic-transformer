from tldextract import tldextract
from server import SemtracServer
import post_queries

__author__ = 'Ameya'

server = SemtracServer()
cursor = server.get_db_cursor()


def get_last_insert_id():
    query = '''SELECT LAST_INSERT_ID() as last_id'''
    cursor.execute(query)
    pwid = cursor.fetchone()['last_id']
    return pwid


def get_names_dictionary():
    query = "SELECT dict_text FROM dictionary WHERE dictset_id = 20 OR dictset_id = 30;"
    cursor.execute(query)
    return [row['dict_text'] for row in cursor.fetchall()]


def get_participant_id(one_way_hash):
    # Insert new participant ID
    query = "SELECT pwset_id FROM password_set WHERE pwset_name='" + one_way_hash + "'"
    cursor.execute(query)
    res = cursor.fetchone()
    if res is not None:
        return res['pwset_id']
    else:
        post_queries.insert_participant_id(one_way_hash)
        query = "SELECT pwset_id FROM password_set WHERE pwset_name='" + one_way_hash + "'"
        cursor.execute(query)
        return cursor.fetchone()['pwset_id']


def get_study_questions(question_type):
    query = "SELECT question_id, question FROM study_questions WHERE type='{}' ORDER BY question_id".format(
        question_type)
    cursor.execute(query)
    questions = cursor.fetchall()
    return questions


def get_participant_logged_websites(participant_id):
    query = '''SELECT website_id, website_text FROM websites WHERE website_id IN (SELECT DISTINCT
                        website_id FROM user_websites INNER JOIN transformed_credentials WHERE user_websites.user_website_id =
                        transformed_credentials.user_website_id AND pwset_id = {})'''.format(participant_id)
    cursor.execute(query)
    websites = cursor.fetchall()
    return websites


def check_website_exists(website_url):
    """Returns website_id of a website_url if it exists"""
    website_id = None
    query = "SELECT website_id FROM websites WHERE website_text = '{}'"
    temp_query = query.format(website_url)
    cursor.execute(temp_query)
    res = cursor.fetchall()
    if len(res) > 0:
        website_id = res[0]['website_id']
    else:
        # check if website_url contains "www." or sub domain is blank
        sub_domain_obj = tldextract.extract(website_url)
        if sub_domain_obj.subdomain.lower() == "www":
            domain_text = "{}.{}".format(sub_domain_obj.domain, sub_domain_obj.suffix)
            temp_query = query.format(domain_text)
            cursor.execute(temp_query)
            res = cursor.fetchall()
            if len(res) > 0:
                website_id = res[0]['website_id']
        elif sub_domain_obj.subdomain.lower() == "":
            domain_text = "www.{}.{}".format(sub_domain_obj.domain, sub_domain_obj.suffix)
            temp_query = query.format(domain_text)
            cursor.execute(query)
            res = cursor.fetchall()
            if len(res) > 0:
                website_id = res[0]['website_id']
    return website_id


def add_website(website_url):
    website_id = None
    post_queries.add_website(website_url)
    query = "SELECT website_id FROM websites WHERE website_text = '{}'".format(website_url)
    cursor.execute(query)
    website_id = cursor.fetchall()[0]['website_id']
    return website_id


def get_transformed_credentials_id(password_set, website_url, password_strength, password_warning):
    """Returns id of transformed_credentials table corresponding to password_set and website_url of user_websites table
    This function first grabs website_id from website_url and then queries user_websites table
    for user_website_id ID."""

    website_id = check_website_exists(website_url)

    if website_id is None:
        # add the website and fetch website_id
        website_id = add_website(website_url)

    query = "SELECT user_website_id FROM user_websites WHERE pwset_id={} AND website_id={}".format(password_set,
                                                                                                   website_id)
    cursor.execute(query)
    res = cursor.fetchall()
    if len(res) > 0:
        user_website_id = res[0]['user_website_id']
    else:
        # Create new entry in user_websites table
        post_queries.insert_new_user_website(website_id, password_set)
        query = "SELECT user_website_id FROM user_websites WHERE website_id = {} AND pwset_id = {}".format(website_id,
                                                                                                           password_set)
        cursor.execute(query)
        user_website_id = cursor.fetchall()[0]['user_website_id']
    # Assuming we now have user_website_id
    # Insert new row in transformed_credentials table and return the transformed_cred_id

    post_queries.insert_transformed_cred_id(user_website_id, password_strength, password_warning)
    query = '''SELECT transformed_cred_id FROM transformed_credentials WHERE user_website_id = {} ORDER BY
            transformed_cred_id DESC LIMIT 1'''.format(user_website_id)
    cursor.execute(query)
    transformed_cred_id = cursor.fetchall()[0]['transformed_cred_id']
    return transformed_cred_id