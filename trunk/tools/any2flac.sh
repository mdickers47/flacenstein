#!/bin/sh

set -e

IN=$1
OUT=`basename "$IN" .mp3`.flac
PIPE=/tmp/flacpipe

mkfifo $PIPE || true
mplayer -vc null -vo null -ao pcm:fast:waveheader:file=$PIPE "$IN" &
flac -s $PIPE -o "$OUT"
rm $PIPE
