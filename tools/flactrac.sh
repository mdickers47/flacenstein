#!/bin/sh
#
# A way to extract single tracks from FLACs with embedded cuesheets.
# Usage: $0 flacfile tracknum
# Will echo the list of tracks if tracknum is missing.
#
# Copyright 2008 Michael A. Dickerson.  Permission to use, modify,
# and redistribute granted under the terms of the GNU GPL v2.

FLAC=$1
TRACK=$2

if [ -z "$TRACK" ] ; then
  metaflac --export-tags-to=- "$FLAC" | egrep '^TITLE=' | sed s/TITLE=// | awk '{ printf "%2d %s\n", NR, $0; }'
  exit 0
fi

ARTIST=`metaflac --export-tags-to=- "$FLAC" | egrep '^ARTIST=' | sed s/ARTIST=//`
TITLE=`metaflac --export-tags-to=- "$FLAC" | egrep '^TITLE=' | sed s/TITLE=// | head -n $TRACK | tail -n 1`
FNAME="$ARTIST - $TITLE.wav"

flac -d --cue=$TRACK.1-$((TRACK + 1)).1 -o "$FNAME" "$FLAC"

echo
echo Never mind that, the output file is \"$FNAME\"
