FROM debian:jessie
MAINTAINER Chris Kanich <kaytwo@gmail.com>

ENV BUILD_PACKAGES "python python-dev libmysqlclient-dev python-dateutil python-mysqldb python-pip python-nltk python-mechanize"

RUN apt-get clean && apt-get update && apt-get install -y $BUILD_PACKAGES


RUN pip install beautifulsoup4 oursql tldextract

RUN python -m nltk.downloader brown words wordnet

WORKDIR /app

EXPOSE 443

CMD python -u server.py
