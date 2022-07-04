FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && \
    apt-get upgrade -y && \
     apt-get install build-essential -y && \
     apt-get install gcc gfortran python3-dev libffi-dev -y

RUN pip install -r requirements.txt

COPY . .

RUN groupadd -g 1000 aircon_grp && \
    useradd -r -u 1000 -g aircon_grp aircon_user && \
    chown -R aircon_user /app 

USER aircon_user

ENV PYTHONUNBUFFERED TRUE

ENTRYPOINT ["./entrypoint.sh"]