#!/bin/bash

set -e

: ${EDITOR:=vi}
: ${OUTFILE:=cd.flac}

cdparanoia "1-"

flac -o "$OUTFILE" --delete-input-file -V --padding 262144 cdda.wav

echo 'Creating cuesheet'

TRACKS=$(cdparanoia -Q 2>&1 | awk '/^ *[0-9]+\. / { print $5; }' | tr -d '[]' | tr '.' ':')
I=1
(
  echo 'FILE "cdda.wav" WAVE'
  for T in $TRACKS ; do
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
  for T in $TRACKS ; do
    printf 'TITLE[%d]=\n' $I
    I=$(($I + 1))
  done
) > tags

$EDITOR tags
metaflac --import-tags-from=tags "$OUTFILE"

ARTIST=$(grep 'ARTIST=' tags | cut -d= -f2)
ALBUM=$(grep 'ALBUM=' tags | cut -d= -f2)
if [ -n "$ARTIST" -a -n "$ALBUM" ] ; then
  mv -v "$OUTFILE" "$ARTIST - $ALBUM.flac"
fi
