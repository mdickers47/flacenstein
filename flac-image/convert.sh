#!/bin/sh

set -e

FLAC=$1

MTIME=`stat -f '%Sm' -t '%Y%m%d%H%M.%S' "$FLAC"`
echo mtime was $MTIME

PICTURE=`metaflac --list --block-type=PICTURE "$FLAC"`

if [ -n "$PICTURE" ]; then
  echo $FLAC already has picture: deleting flac-image blocks
  flac-image -d "$FLAC"
  metaflac --sort-padding "$FLAC"
  touch -t$MTIME "$FLAC"
  exit 0
fi

IMG=`flac-image -l "$FLAC" | grep '^Name:' | head -n 1 | cut -c7-`
# flac-image -l updates mtime for some reason which appears to be
# libflac's fault.
touch -t$MTIME "$FLAC"
echo image block was $IMG

if [ -z "$IMG" ]; then
  echo 'No flac-image blocks'
  exit 1
fi

flac-image -x "$FLAC"
metaflac --import-picture-from=$IMG "$FLAC"
flac-image -d "$FLAC"
metaflac --sort-padding "$FLAC"
touch -t$MTIME "$FLAC"
rm $IMG