import unicodedata
import include.participant as participant
import database.get_queries as get_queries
import include.util as utils
import transformation.segmentation as segmentation

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

        segmentation.segment_password(clear_password_uri_decoded, True, self.participantObj.get_participant_id())
        self.posTagging()
        self.grammarGeneration(transformed_cred_id, clearPassword=clearPasswordURIDecoded)

        # Delete original password after transformation
        self.clearOriginalData()

        # Transform usernames semantically. We'll use the same functions for now.
        # as the procedure is same, except that we dont have to store grammar.
        # First check if username is email, if it is then extract email username and transform only the
        # username
        email_split_flag = False
        if re.match("[^@]+@[^@]+\.[^@]+", clearUsernameURIDecoded):
            email_username = clearUsernameURIDecoded.split("@")[0]
            email_split_flag = True
        else:
            email_username = clearUsernameURIDecoded
        self.segmentPassword(email_username, False)
        self.posTagging()
        self.grammarGeneration(transformed_cred_id, type="username")

        if email_split_flag:
            # Now append the email domain to the transformed Username
            email_domain = "@" + clearUsernameURIDecoded.split("@")[1]
            append_email_domain(db, transformed_cred_id, email_domain)

        # store clearUsername in participantObj
        participantObj.set_active_username(clearUsernameURIDecoded)
        self.clearOriginalData()

        participantObj.reset_active_website()