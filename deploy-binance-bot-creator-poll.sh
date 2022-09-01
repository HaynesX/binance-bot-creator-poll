#!/bin/bash

set -e

DOCKER_IMAGE_TAG=$1


cd binance-bot-creator-poll

echo "Shutting Down Previous Containers."

sudo docker-compose -f docker-compose-binance-bot-creator-poll.yaml down

cd ..

echo "Deleting previous directory"

rm -rf binance-bot-creator-poll

echo "Cloning Repo"

git clone https://github.com/HaynesX/binance-bot-creator-poll.git

cd binance-bot-creator-poll

echo "Checkout new version"

git checkout tags/$DOCKER_IMAGE_TAG

echo "Starting Docker Container for Image $DOCKER_IMAGE_TAG"

sudo TAG=$DOCKER_IMAGE_TAG docker-compose -f docker-compose-binance-bot-creator-poll.yaml up -d


