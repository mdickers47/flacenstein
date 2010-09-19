#!/bin/sh

for F in "$@" ; do
  flac -d "$F" -o - | lame - "`basename "$F" .flac`.mp3"
done
