
def escape (text, characters):
    """ Escape the given characters from a string. """
    for character in characters:
        text = text.replace(character, '\\' + character)
    return text 


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
    print escape("ghjkl;\\\'", ["\\", "'" ])