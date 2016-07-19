import MySQLdb
import sys

__author__ = 'Ameya'

toEscape = ['\\', '\'', ' ']

def escape (text, characters):
    """ Escape the given characters from a string. """
    for character in characters:
        text = text.replace(character, '\\' + character)
    return text

def connection():
    # credentials = util.dbcredentials()
    return MySQLdb.connect(host = 'localhost',  # your host, usually localhost
                 user = 'root',   # your username
                 passwd = 'sitscomp',  # your password
                 db = "passwords")


def get_wordset_id(cursor, pos):
    global pos_dict
    query = "SELECT wordset_id from wordlist_set WHERE wordset_name = '" + pos + "'"
    cursor.execute(query)
    if cursor.rowcount == 1:
        # Get the wordset_id
        wordset_id = cursor.fetchall()[0][0]
        pos_dict[pos] = wordset_id
        return wordset_id
    else:
        # Insert the POS
        query = "INSERT INTO wordlist_set SET wordset_name = '" + pos + "'"
        cursor.execute(query)
        query = "SELECT wordset_id from wordlist_set WHERE wordset_name = '" + pos + "'"
        cursor.execute(query)
        wordset_id = cursor.fetchall()[0][0]
        pos_dict[pos] = wordset_id
        return wordset_id


f = open("../../files/coca_500k.csv")
lines = [line.rstrip('\n') for line in f]
conn = connection()
cursor = conn.cursor()

# Initialize POS dictionary
pos_dict = dict()

for line in lines:
    segments = line.split()
    word = segments[1]
    pos = segments[2]

    # Sanitize pos and word
    pos = escape(pos, toEscape)
    word = escape(word, toEscape)
    if word == "" or pos == "":
        continue

    # Check if we have pos into pos_dict
    if pos in pos_dict:
        wordset_id = pos_dict[pos]
    else:
        wordset_id = get_wordset_id(cursor, pos)

    # Insert the word in wordlist
    query = "INSERT INTO wordlist SET wordset_id = " + str(wordset_id) + ", wordlist_text = '" + word + "'"
    cursor.execute(query)

conn.commit()
conn.close()