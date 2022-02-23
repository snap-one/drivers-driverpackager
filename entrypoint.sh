#!/bin/sh

cd $1

if [ -z "$4" ]; then
    python3 /app/dp3/driverpackager.py -v ./ $3 $2 --driver-version $4
        else
    python3 /app/dp3/driverpackager.py -v ./ $3 $2
fi
