import include.participant as participant
import database.get_queries as get_queries

__author__ = 'Ameya'


class Controllers():
    def __init__(self):
        self.participantObj = participant.Participant()

    def new_participant_record(self, db, one_way_hash):
        participant_id = get_queries.get_participant_id(db, one_way_hash)
        self.participantObj.set_participant_id(participant_id)
        return participant_id