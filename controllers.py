

__author__ = 'Ameya'


class Controllers():
    def __init__(self):
        pass

    def new_participant_record(self):
        participant_id = get_participant_id(db, one_way_hash)
        participantObj.set_participant_id(participant_id)
        return participant_id