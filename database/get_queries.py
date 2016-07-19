from server import SemtracServer

__author__ = 'Ameya'


server = SemtracServer()
cursor = server.get_db_cursor()


def get_names_dictionary():
    query = "SELECT dict_text FROM dictionary where dictset_id = 20 or dictset_id = 30;"
    cursor.execute(query)
    return [row['dict_text'] for row in cursor.fetchall()]


def get_participant_id(db, one_way_hash):
    # Insert new participant ID
    cursor = db.get_cursor()
    query = "SELECT pwset_id FROM password_set WHERE pwset_name='" + one_way_hash + "'"
    cursor.execute(query)
    res = cursor.fetchone()
    if res is not None:
        return res['pwset_id']
    else:
        query = "INSERT INTO password_set SET pwset_name='" + one_way_hash + "', max_pass_length=50"
        cursor.execute(query)
        db.commit()
        query = "SELECT pwset_id FROM password_set WHERE pwset_name='" + one_way_hash + "'"
        cursor.execute(query)
        return cursor.fetchone()['pwset_id']