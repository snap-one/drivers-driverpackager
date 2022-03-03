#!/bin/sh

cd $INPUT_PROJECTDIR

cmd="python3 /app/dp3/driverpackager.py -v ./ $INPUT_OUTPUTDIR $INPUT_C4ZPROJ"

if [ ! -z "$INPUT_VERSION" ]; then
    cmd="$cmd --driver-version $INPUT_VERSION"
fi

if [ ! -z $INPUT_UPDATEMODIFIED] && [ ! $INPUT_UPDATEMODIFIED = false ]; then
    cmd="$cmd --update-modified"
fi

eval $cmd
