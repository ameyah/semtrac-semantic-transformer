import urllib
import urlparse
import os
import re
from tldextract import tldextract


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


def url_decode(text):
    return urllib.unquote(urllib.unquote(text))


def is_int(s):
    reg_isint = re.compile("^[\d]+$")
    return bool(reg_isint.match(s))


def is_num_sc_chunk(s):
    reg_is_num_sc_chunk = re.compile("^[\W0-9_]+$")
    return bool(reg_is_num_sc_chunk.match(s))


def is_sc_chunk(s):
    reg_is_sc_chunk = re.compile("^[\W_]+$")
    return bool(reg_is_sc_chunk.match(s))


def is_char_chunk(s):
    reg_is_char_chunk = re.compile("^[a-zA-Z]+$")
    return bool(reg_is_char_chunk.match(s))


def escape(text, characters=None):
    """ Escape the given characters from a string. """
    if characters is None:
        characters = ['\\', '\'', ' ']
    for character in characters:
        text = text.replace(character, '\\' + character)
    return text


def get_get_param(path, key):
    parsed = urlparse.urlparse(path)
    return urlparse.parse_qs(parsed.query)[key][0]


def check_website_syntactic_similarity(url1, url2):
    if url1.lower() == url2.lower():
        return True
    else:
        subDomainObjUrl1 = tldextract.extract(url1.lower())
        subDomainObjUrl2 = tldextract.extract(url2.lower())
        # first check whether domain and extension match
        if (subDomainObjUrl1.domain == subDomainObjUrl2.domain) and (
                    subDomainObjUrl1.suffix == subDomainObjUrl2.suffix):
            # now check subdomain match
            if (subDomainObjUrl1.subdomain == subDomainObjUrl2.subdomain) or \
                    (subDomainObjUrl1.subdomain == "" and subDomainObjUrl2.subdomain == "www") or \
                    (subDomainObjUrl1.subdomain == "www" and subDomainObjUrl2.subdomain == ""):
                return True
            else:
                return False
        else:
            return False