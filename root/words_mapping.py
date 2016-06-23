

__author__ = 'Ameya'


word_mapping = dict()


def clear_word_mapping():
    global word_mapping
    word_mapping.clear()


def get_word_mapping(word):
    global word_mapping
    return word_mapping[str(word)] if str(word) in word_mapping else None


def insert_word_mapping(word, transformed_word):
    global word_mapping
    word_mapping[str(word)] = transformed_word