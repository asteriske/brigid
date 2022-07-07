FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && \
    apt-get upgrade -y && \
     apt-get install build-essential -y && \
     apt-get install gcc gfortran python3-dev libffi-dev dnsutils net-tools netcat -y

RUN pip install -r requirements.txt

COPY . .

RUN groupadd -g 1000 brigid_grp && \
    useradd -r -u 1000 -g brigid_grp brigid_user && \
    chown -R brigid_user /app 

USER brigid_user

ENV PYTHONUNBUFFERED TRUE

ENTRYPOINT ["./entrypoint.sh"]
