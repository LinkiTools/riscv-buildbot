FROM python:3.6.2-stretch

LABEL maintainer="Paulo Matos <pmatos@linki.tools>"

ADD . /master
WORKDIR /master

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8010
EXPOSE 9989

CMD buildbot start .
