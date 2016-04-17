#!/bin/sh
#
# Wrapper that makes it easy to do the two most common metaflac things:
# print tags and edit tags.  Use the -e option to edit in $EDITOR.
# 
# Copyright 2008 Michael A. Dickerson.  Permission to use, modify
# and redistribute granted under the terms of the GNU GPL v2.

set -e

while getopts e F ; do
  case $F in
  e) EDIT=1 ;;
  \?) echo "only option is -e"; exit 1 ;;
  esac
done
shift $(($OPTIND - 1))

MD5=`which md5sum || which md5`

for F in "$@" ; do
  if [ -n "$EDIT" ]; then
    TMP=`mktemp -t tags.XXXXXX`
    metaflac --export-tags-to=$TMP "$F"
    PRE_MD5=`$MD5 $TMP`
    ${EDITOR:-vi} $TMP || exit $?
    POST_MD5=`$MD5 $TMP`
    if [ "$PRE_MD5" != "$POST_MD5" ]; then
      echo -n "Updating tags in $F..."
      metaflac --remove-all-tags "$F"
      metaflac --import-tags-from=$TMP "$F"
      echo "done."
    else
      echo -n "Tags not changed."
    fi
  else
    metaflac --export-tags-to=- "$F"
  fi
done
