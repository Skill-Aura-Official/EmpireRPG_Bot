FROM python:latest

WORKDIR /app
COPY requirements.txt ./requirements.txt

RUN apt-get update -y && apt-get upgrade -y

RUN pip3 install -U pip setuptools
RUN pip3 install -U -r requirements.txt

COPY MythicRPG ./MythicRPG
CMD ["python3","-m","MythicRPG"]
