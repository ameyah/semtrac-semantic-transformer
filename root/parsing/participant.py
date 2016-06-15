__author__ = 'Ameya'


class Participant():
    def __init__(self):
        self.participant_id = 0
        self.active_website = ''
        self.previous_active_website = ''
        self.transformed_cred_id = 0

    def get_participant_id(self):
        return self.participant_id

    def get_active_website(self):
        return self.active_website

    def get_previous_active_website(self):
        return self.previous_active_website

    def get_transformed_cred_id(self):
        return self.transformed_cred_id

    def set_active_website(self, url):
        self.active_website = url

    def set_participant_id(self, id):
        self.participant_id = id

    def set_transformed_cred_id(self, id):
        self.transformed_cred_id = id

    def reset_active_website(self):
        self.previous_active_website = self.active_website
        self.active_website = ''