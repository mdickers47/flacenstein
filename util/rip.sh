#!/bin/bash

set -e

: ${EDITOR:=vi}
: ${OUTFILE:=cd.flac}

cdparanoia "1-"

flac -o "$OUTFILE" --delete-input-file -V --padding 262144 cdda.wav

echo 'Creating cuesheet'

# note that the extra ( ) causes bash to make TRACKS an array
TRACKS=($(cdparanoia -Q 2>&1 | awk '/^ *[0-9]+\. / { print $5; }' | tr -d '[]' | tr '.' ':'))

if [ "${TRACKS[0]}" != "00:00:00" ]; then
  echo "warning: TOC wanted track 1 to start at ${TRACKS[0]} but it can't"
  TRACKS[0]="00:00:00"
fi

I=1
(
  echo 'FILE "cdda.wav" WAVE'
  for T in ${TRACKS[@]} ; do
    printf '  TRACK %02d AUDIO\n' $I
    printf '    INDEX 01 %s\n' $T
    I=$(($I + 1))
  done
) | metaflac --import-cuesheet-from=- "$OUTFILE"

echo 'Creating tags'

I=1
(
  echo 'ARTIST='
  echo 'ALBUM='
  echo 'DATE='
  for T in ${TRACKS[@]} ; do
    printf 'TITLE[%d]=\n' $I
    I=$(($I + 1))
  done
) > tags.tmp

$EDITOR tags.tmp
metaflac --import-tags-from=tags.tmp "$OUTFILE"

ARTIST=$(grep 'ARTIST=' tags.tmp | cut -d= -f2)
ALBUM=$(grep 'ALBUM=' tags.tmp | cut -d= -f2)
if [ -n "$ARTIST" -a -n "$ALBUM" ] ; then
  mv -v "$OUTFILE" "$ARTIST - $ALBUM.flac"
fi

echo "Remember to do the cover:"
echo "metaflac --import-picture-from=xyz '$ARTIST - $ALBUM.flac'"
