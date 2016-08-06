import random
import string
import urllib
import urlparse
import os
import re
from tldextract import tldextract
import cgi


def dbcredentials(root_path):
    f = open(abspath(root_path, 'db_credentials.conf'))

    credentials = dict()
    for line in f:
        key, value = map(lambda x: x.strip(),line.split(':'))
        if "MYSQL_" + key in os.environ.keys():
          credentials[key] = os.environ["MYSQL_" + key]
        else:
          credentials[key] = value

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


def generate_n_digit_random(n):
    range_start = 10 ** (n - 1)
    range_end = (10 ** n) - 1
    return random.randint(range_start, range_end)


def generate_n_char_random(n):
    return ''.join(random.choice(string.lowercase) for i in range(n))


def generate_n_symbol_random(n):
    return ''.join(random.choice(string.punctuation) for i in range(n))


def stringify_pattern(tags):
    return ''.join(['({})'.format(tag) for tag in tags])


def get_maximum_list_length(dictionary):
    return len(dictionary[sorted(dictionary, key=lambda x: len(dictionary[x]), reverse=True)[0]])


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


def get_post_data(headers, rfile):
    ctype, pdict = cgi.parse_header(headers.getheader('content-type'))
    if ctype == 'multipart/form-data':
        postvars = cgi.parse_multipart(rfile, pdict)
    elif ctype == 'application/x-www-form-urlencoded':
        length = int(headers.getheader('content-length'))
        postvars = cgi.parse_qs(rfile.read(length), keep_blank_values=1)
    else:
        postvars = ''
    return postvars


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


def check_website_importance(probability):
    if probability is None:
        importance = False
    else:
        if probability >= 0.50:
            importance = True
        else:
            importance = False
    return importance
