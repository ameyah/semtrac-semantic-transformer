import hashlib


def escape(text, characters):
    """ Escape the given characters from a string. """
    for character in characters:
        text = text.replace(character, '\\' + character)
    return text


def get_maximum_list_length(dictionary):
    return len(dictionary[sorted(dictionary, key=lambda x: len(dictionary[x]), reverse=True)[0]])


def generate_all_list_permutations(mapping_dict):
    """This function takes input as a dictionary of lists and generates all possible mappings
    Mappings can be used to replace key with values
    Returns list of all possible mappings"""
    result_list = []
    max_list_length = get_maximum_list_length(mapping_dict)
    for i in mapping_dict:  # for each element in mapping_dict
        for j in range(0, len(mapping_dict[i])):  # for each element of list inside element of dict
            for n in range(0, max_list_length):  # to map j with each possible list element of other dict elements
                temp_map = {}
                for k in mapping_dict:
                    if k == i:
                        temp_map[k] = mapping_dict[k][j]
                    else:
                        if len(mapping_dict[k]) > n:  # not all elements of dict have same length lists
                            temp_map[k] = mapping_dict[k][n]
                        else:
                            temp_map[k] = mapping_dict[k][len(mapping_dict[k]) - 1]
                if temp_map not in result_list:
                    result_list.append(temp_map)

    return result_list


def generate_md5_hash(word):
    """Returns md5 hash of the word"""
    return hashlib.md5(word).hexdigest()


def calculate_new_probability_remove_user(old_probability, old_users, user_probability):
    try:
        current_total_probability = float(old_probability) * int(old_users)  # probability * no_users
        new_total_probability = current_total_probability - int(user_probability)
        new_average_probability = new_total_probability / (int(old_users) - 1)
    except ZeroDivisionError:
        return None
    return new_average_probability


def calculate_new_probability_add_user(old_probability, old_users, user_probability):
    current_total_probability = float(old_probability) * int(old_users)  # probability * no_users
    new_total_probability = current_total_probability + int(user_probability)
    new_average_probability = new_total_probability / (int(old_users) + 1)
    return new_average_probability


if __name__ == '__main__':
    print escape("ghjkl;\\\'", ["\\", "'"])