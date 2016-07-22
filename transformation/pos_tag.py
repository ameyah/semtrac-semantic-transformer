import traceback
from include.cache_data import TempWordBuffer, Cache
from include.timer import Timer

__author__ = 'Ameya'

cache = Cache()


def pos_tag_word(participant_id):
    try:
        word_buffer_obj = TempWordBuffer(participant_id, save_cachesize=500000)
        counter = 0

        with Timer("POS tagging"):
            total = word_buffer_obj.sets_size
            lastpw = None

            while word_buffer_obj.has_next():
                pwd = word_buffer_obj.next_password()  # list of Fragment
                pwd_str = pwd[0].password

                counter += 1

                # filters segments that are not dictionary words
                pwd = [f for f in pwd if f.dictset_id <= 90]

                # only recalculate POS if this password is diff than previous
                if pwd_str != lastpw:
                    # extracts to a list of strings and tags them
                    pos_tagged = cache.pos_tag_words([f.word for f in pwd])

                for i, f in enumerate(pwd):
                    pos = pos_tagged[i][1]  # Brown pos tag
                    f.pos = pos

                lastpw = pwd_str

                if counter % 100000 == 0:
                    print "{} passwords processed. {}% completed..." \
                        .format(counter, (float(counter) / total) * 100)

    except:
        traceback.print_exc()