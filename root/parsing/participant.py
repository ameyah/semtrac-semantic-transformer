__author__ = 'Ameya'


class Participant():
    def __init__(self):
        self.participant_id = 0
        self.active_website = ''

    def get_participant_id(self):
        return self.participant_id

    def set_participant_id(self, id):
        self.participant_id = id

    def reset_active_website(self):
        self.active_website = ''

    def get_active_website(self):
        return self.active_website

    def set_active_website(self, url):
        self.active_website = url