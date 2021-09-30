#!/bin/sh

SOURCE_DIR=$1
C4ZPROJ=$2
OUTPUT_DIR=$3
# Skip possitional arguments
shift; shift; shift;

cd $SOURCE_DIR

python3 /app/dp3/driverpackager.py -v ./ $OUTPUT_DIR $C4ZPROJ $@
