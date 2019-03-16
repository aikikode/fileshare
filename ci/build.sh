#!/usr/bin/env bash

set -eux

cd $(dirname $0)

docker-compose build
docker-compose run -u$(id -u):$(id -g) builddeb ./build_deb.sh
