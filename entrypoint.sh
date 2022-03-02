#!/bin/sh

cd $1

cmd="python3 /app/dp3/driverpackager.py -v ./ $3 $2"

if [ ! -z "$4" ]; then
    cmd="$cmd --driver-version $4"
fi

if [ ! -z "$5" ]; then
    cmd="$cmd --update-modified $5"
fi

eval $cmd
