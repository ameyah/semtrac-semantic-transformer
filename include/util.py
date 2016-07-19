
import os


def dbcredentials(root_path):
    f = open(abspath(root_path, 'db_credentials.conf'))

    credentials = dict()

    for line in f:
        key, value = line.split(':')
        credentials[key.strip()] = value.strip()

    return credentials


def abspath(root_path, filename):
    """ Returns the absolute path for a file relative of the
    location from which the module was loaded (usually root).
    This method allows you to load an internal file independent
    of the location the program was called from. 
    """
    dir = os.path.dirname(root_path)
    return os.path.join(dir, filename)
