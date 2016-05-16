#Semantic Guesser

##Todo

1) Modify remote_claws_tagger.py to create the pickles subdirectory if it is not already created

2) Modify the pos_tagger.py script to call remote_claws_tagger.py if claws tagger has not been run (the pickles folder is empty / non-existant)


##Dependencies

[Python 2.7] (https://www.python.org/downloads/)

[Oursql](https://launchpad.net/oursql)

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

Before you begin using the parsing and classification scripts, a MySQL database must be set up and the required data included. Unpack `db/sql.tar.gz` and run the following lines:

    mysql -u user -p < root/db/passwords_schema.sql
    mysql -u user -p < root/db/lexicon.sql

The above commands will create the database schema and insert the lexicon.

###Adding more training data

Training data in the db is organized with password sets. A password set is a collection of passwords (e.g., a password
leak) used for training a grammar. To add a password set, you need to insert an entry into the table `password_set`. For
example:

    INSERT INTO password_set VALUES (id, name, max_pass_length);

where `id` is an unambiguous ID of your choice. Next, add all passwords to the table `passwords`, setting the value of the field `pwset_id` accordingly.

If you would like to have the RockYou passwords on the db, download [this](https://www.dropbox.com/s/bnxmxdvrkkz5lra/rockyou_ordered.sql.tar.gz) script and run it on your database:

    mysql -u user -p < root/db/rockyou.sql

Note that this will add the RY passwords with the password_set ID 1, so be careful if you already have data in the passwords table.

###Authentication

Make sure you modify the file root/db_credentials.conf with your MYSQL credentials.

###Parsing
wordminer.py connects to a database containing the passwords and dictionaries to perform password segmentation. The results are saved into the database.

**Important Note**
For performance reasons, make sure the passwords table is ordered by pass_text before running wordminer.py. Wordminer works in chunks of 100'000 words, and used to take 1+ days to run. The passwords table contains ~32'000'000 records, and each time 100'000 were fetched, the entire table was ordered by pass_text. As a result, preordering the table will speed up queries tremendously (only takes ~7 hours now on a high powered computer). If the RockYou passwords were loaded from the file provided above, they are already sorted.

For example, to parse a group of passwords whose ID in the database is 1:

    cd parsing/
    python wordminer.py 1

For more options:

    python wordminer.py --help

### Classification

Before generating the grammar. You need to run the scripts for POS tagging and semantic classification.
Assuming you're targeting the group of passwords 1:

    cd root/
    python pos_tagger.py 1

### Grammar generation

    cd root/
    python grammar.py 1

By default, the grammar files will be saved in a subdirectory of grammar/ identified by the ID of the corresponding password list, but you can define a custom path by passsing the argument `--path`. As usual, you can see more options by passing `--help`.

Grammars can be generated with a variety of tags, depending on how much complexity you want, ranging from basic string type tags (word, number, special char) to more complex wordnet tags (e.g., v.love.01). This can set using the parameter `--tags`.

### Generating guesses

Compile guessmaker with:

    cd root/
    make all
    ./guessmaker -s 1

For more options:

    ./guessmaker --help

## Publications

Veras, Rafael, Christopher Collins, and Julie Thorpe. "On the semantic patterns of passwords and their security impact." Network and Distributed System Security Symposium (NDSS’14). 2014. [Link] (http://thorpe.hrl.uoit.ca/documents/On_the_Semantic_Patterns_of_Passwords_and_their_Security_Impact_NDSS2014.pdf)

## Credits

Rafael Veras, Julie Thorpe and Christopher Collins
[Vialab][vialab] - [University of Ontario Institute of Technology][uoit]


Special thanks to Brent McRae, who helped fixing many bugs.

[vialab]: http://vialab.science.uoit.ca
[uoit]:   http://uoit.ca

