#SemTrAC Semantic Transformer

##Dependencies

[Python 2.7] (https://www.python.org/downloads/)

[MySQLDb]
    Install with "pip install mysql-python"

[dateutil]
    Install with "pip install python-dateutil"

[NLTK](http://www.nltk.org/). After installing it, you should also [install the following data packages](http://www.nltk.org/data.html):

  * Brown Corpus
  * Wordnet
  * Word Lists

[BeautifulSoup4](http://www.crummy.com/software/BeautifulSoup/)
     Install with "pip install beautifulsoup4"

[Mechanize](https://pypi.python.org/pypi/mechanize/0.2.5)
     Install with "pip install mechanize"

##Usage

###Before you start (data dependencies)

Before you begin using the parsing and classification scripts, a MySQL database must be set up and the required data included. Unpack `db/passwords_full_improved_2.tar.gz` and run the following lines:

    mysql -u user -p passwords < /path/to/passwords_full_improved_2.sql

The above commands will create the database schema and insert the data.

###Running

Execute "python server.py" from the command line. Make sure the port number 443 is not used by any other service running on your local machine.


* Semantic Transformer is a part of the project to study how people create passwords and to analyze them.
    https://steel.isi.edu/Projects/PASS