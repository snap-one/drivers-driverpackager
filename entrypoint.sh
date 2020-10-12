#!/bin/sh

STARTING_DIR=$PWD

cd $1

python3 /app/dp3/driverpackager.py -v ./ $STARTING_DIR $2