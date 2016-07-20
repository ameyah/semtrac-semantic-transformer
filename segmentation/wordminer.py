from include.cache_data import TempClearTextWriteBuffer

__author__ = 'Ameya'


def segment_password(clear_text, check_mangling):
    wbuff = TempClearTextWriteBuffer(dictionary, 100000)
    if len(clearPassword) == 0:
        return
    if clearPassword.strip(" ") == '':
        return

    # add Password to database temporarily.
    pass_id = addSocketPassword(db, clearPassword, participantObj.get_participant_id())

    res = mineLine(db, clearPassword, dictionary, freqInfo, checkSpecialChars)
    if options.verbose:
        print "[Done]"

    # store results
    if len(res) > 0:
        flush = wbuff.addCommit(pass_id, res)

    wbuff._flush()  # flush the rest