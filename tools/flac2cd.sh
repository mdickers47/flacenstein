#!/bin/sh
#
# flac2cd.sh - Recreate a CD from FLAC file $1.
# Written 4 Apr 2007 by M. Dickerson (too trivial for a license,
# don't you think?)

set -e

while getopts k F ; do
  case $F in
  k) KEEP=1 ;;
  \?) echo "only option is -k"; exit 1 ;;
  esac
done
shift $(($OPTIND - 1))

ME=`basename $0`
AUDIO=`mktemp -t $ME`
CUE=`mktemp -t $ME`
FLAC=$1

echo FILE "$AUDIO" WAVE > $CUE
metaflac --export-cuesheet-to=- "$FLAC" | grep -v FILE >> $CUE
flac -f -o $AUDIO -d "$FLAC"
cdrecord -dao --cuefile=$CUE

if [ -z "$KEEP" ] ; then
  rm $CUE $AUDIO
else
  echo "To burn another cd: cdrecord -dao cuefile=$CUE"
  echo "To clean up: rm $CUE $AUDIO"
fi
