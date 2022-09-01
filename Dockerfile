FROM python:3.8

RUN mkdir -p /home/binance-bot-creator-poll
WORKDIR /home/binance-bot-creator-poll

COPY requirements.txt /home/binance-bot-creator-poll

RUN pip install -r /home/binance-bot-creator-poll/requirements.txt

COPY . /home/binance-bot-creator-poll