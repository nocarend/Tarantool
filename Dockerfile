FROM python:3.11.3-buster

COPY main.py main.py
COPY requirements.txt requirements.txt
COPY .env .env
COPY boot.sh boot.sh

RUN chmod +x /boot.sh
ENTRYPOINT "./boot.sh"