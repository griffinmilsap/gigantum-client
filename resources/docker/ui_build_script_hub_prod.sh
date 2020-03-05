#!/usr/bin/env bash

set -e

# Update node
cd /opt/ui
yarn install

# Run relay
yarn relay

# Run build
yarn build:cloud:prod
