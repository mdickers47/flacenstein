#!/bin/sh
set -e

TOTAL=0

for F in "$@" ; do
  SIZE=`metaflac --list "$F" | grep 'total samples' | cut -d: -f2`
  SIZE=$(( $SIZE / 44100 ))
  printf '%4d %s\n' $SIZE "$F"
  TOTAL=$(( $TOTAL + $SIZE ))
done

if [ $TOTAL -ne $SIZE ]; then
  echo ---------------------------
  printf '%4d total\n' $TOTAL
fi
