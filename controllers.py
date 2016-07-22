import unicodedata
import re
import include.participant as participant
import database.get_queries as get_queries
import include.util as utils
import transformation.segmentation as segmentation
import transformation.pos_tag as pos_tag
import transformation.generate_grammar as generate_grammar
from database import post_queries

__author__ = 'Ameya'


class Controllers():
    def __init__(self):
        self.participantObj = participant.Participant()

    def new_participant_record(self, one_way_hash):
        participant_id = get_queries.get_participant_id(one_way_hash)
        self.participantObj.set_participant_id(participant_id)
        return participant_id

    def get_study_questions(self, questions_type):
        if questions_type == "CURRENT" or questions_type == "RISK" or questions_type == "POST":
            questions = get_queries.get_study_questions(questions_type)
            questions = [{"question_id": int(elem['question_id']),
                          "question": unicodedata.normalize('NFKD', elem['question']).encode('ascii', 'ignore')} for
                         elem in questions]
            if len(questions) > 0:
                if questions_type == "POST":
                    websites = get_queries.get_participant_logged_websites(self.participantObj.get_participant_id())
                    result_obj = {
                        "questions": questions,
                        "websites": []
                    }
                    for website in websites:
                        website_obj = {
                            "id": website['website_id'],
                            "text": website['website_text']
                        }
                        result_obj['websites'].append(website_obj)
                    return result_obj
                return questions

    @staticmethod
    def clear_plain_text_data():
        post_queries.clear_plain_text_data()

    def transform_credentials(self, website_info_dict):
        # For websiteUrl, first check whether participantObj has an active url
        active_website = self.participantObj.get_active_website()
        if active_website != '':
            website_url = active_website
        else:
            website_url = website_info_dict['active_url']
            previous_active_website = self.participantObj.get_previous_active_website()
            if utils.check_website_syntactic_similarity(website_url, previous_active_website):
                website_url = previous_active_website
        clear_password_uri_decoded = utils.url_decode(website_info_dict['clear_password'])
        clear_username_uri_decoded = utils.url_decode(website_info_dict['clear_username'])

        # First insert the login website in the database
        transformed_cred_id = get_queries.get_transformed_credentials_id(self.participantObj.get_participant_id(),
                                                                         website_url,
                                                                         website_info_dict['password_strength'],
                                                                         website_info_dict['password_warning'])
        self.participantObj.set_transformed_cred_id(transformed_cred_id)

        segmentation.segment_word(clear_password_uri_decoded, True, self.participantObj.get_participant_id())
        pos_tag.pos_tag_word(self.participantObj.get_participant_id())
        generate_grammar.generate_grammar(transformed_cred_id, transformed_cred_id,
                                          clear_password=clear_password_uri_decoded)

        # Delete original password after transformation
        self.clear_plain_text_data()

        # Transform usernames semantically. We'll use the same functions for now.
        # as the procedure is same, except that we dont have to store grammar.
        # First check if username is email, if it is then extract email username and transform only the
        # username
        email_split_flag = False
        if re.match("[^@]+@[^@]+\.[^@]+", clear_username_uri_decoded):
            email_username = clear_username_uri_decoded.split("@")[0]
            email_split_flag = True
        else:
            email_username = clear_username_uri_decoded
        segmentation.segment_word(email_username, False, self.participantObj.get_participant_id())
        pos_tag.pos_tag_word(self.participantObj.get_participant_id())
        generate_grammar.generate_grammar(self.participantObj.get_participant_id(), transformed_cred_id,
                                          type="username")

        if email_split_flag:
            # Now append the email domain to the transformed Username
            email_domain = "@" + clear_username_uri_decoded.split("@")[1]
            post_queries.append_email_domain_username(transformed_cred_id, email_domain)

        # store clearUsername in participantObj
        self.participantObj.set_active_username(clear_username_uri_decoded)
        self.clear_plain_text_data()

        self.participantObj.reset_active_website()