#!/usr/bin/python
"""
A program that checks a Flacenstein-style FLAC file for all kinds of things
that can go wrong, such as missing COMMENT blocks, number of tracks in cuesheet
does not match number of TITLE tags, etc.  Invoke with the name of a FLAC file
as the only argument.

The following shell construct may be useful if you want to check a lot of
files:
$ find /path/to/flacs -name \*.flac -print -exec flac-lint.py {} \;

Copyright (c) 2005 Michael A. Dickerson.  Modification and redistribution are
permitted under the terms of the GNU General Public License, version 2.
"""

import re
import sys

import flac.metadata

LV_DEBUG = 0
LV_WARN  = 1
LV_ERROR = 2

msglevel = LV_WARN

def msg(level, msg):
    if level < msglevel: return
    if level == LV_DEBUG:
        print "d:",
    elif level == LV_WARN:
        print "W:",
    elif level == LV_ERROR:
        print "E:",
    print msg
    
class flacfile:
    """
    just a container for the metadata we extract
    """
    had_cuesheet = False
    had_tags = False
    comments = {}
    image_blocks = 0

# parse all the metadata blocks in the flac file
    
chain = flac.metadata.Chain()
chain.read(sys.argv[1])
it = flac.metadata.Iterator()
it.init(chain)
while True:
    block = it.get_block()
    if block.type == flac.metadata.STREAMINFO:
        streaminfo = block.data.stream_info
        flacfile.total_samples = streaminfo.total_samples
    elif block.type == flac.metadata.VORBIS_COMMENT:
        flacfile.had_tags = True
        c = block.data.vorbis_comment
        for i in range(c.num_comments):
            name, val = re.split('=', c.comments[i], 2)
            if not name in flacfile.comments:
                flacfile.comments[name] = val
            elif isinstance(flacfile.comments[name], list):
                flacfile.comments[name].append(val)
            else:
                flacfile.comments[name] = [flacfile.comments[name], val]
    elif block.type == flac.metadata.CUESHEET:
        flacfile.had_cuesheet = True
        flacfile.cuesheet = block.data.cue_sheet
    elif block.type == flac.metadata.APPLICATION:
        app = block.data.application
        msg(LV_DEBUG, 'found application block with id %s' % app.id)
        if app.id == 'imag': flacfile.image_blocks += 1
        
    if not it.next(): break

# we have all the information we can get from the flac file, now inspect it

if (flacfile.had_cuesheet == False):
    msg(LV_ERROR, "missing cuesheet block")
else:
    if 'TITLE' in flacfile.comments:
        if (flacfile.cuesheet.num_tracks - 1 != len(flacfile.comments['TITLE'])):
            msg(LV_ERROR, '%d tracks in cuesheet, but %d TITLE tags' \
                % (flacfile.cuesheet.num_tracks - 1, len(flacfile.comments['TITLE'])))

if flacfile.image_blocks == 0:
    msg(LV_WARN, 'missing flac-image APPLICATION block')
elif flacfile.image_blocks > 1:
    msg(LV_DEBUG, 'multiple flac-image APPLICATION blocks')
               
if (flacfile.had_tags == False):
    msg(LV_ERROR, "missing VORBIS_COMMENT block")
else:
    if not 'ARTIST' in flacfile.comments or not flacfile.comments['ARTIST']:
        msg(LV_ERROR, "missing ARTIST tag")
    if not 'ALBUM' in flacfile.comments or not flacfile.comments['ALBUM']:
        msg(LV_ERROR, "missing ALBUM tag")
    if 'ARTIST' in flacfile.comments and 'ALBUM' in flacfile.comments:
        pattern = '%s - %s.flac$' % (flacfile.comments['ARTIST'], flacfile.comments['ALBUM'])
        if not re.search(pattern, sys.argv[1]):
            msg(LV_WARN, "file name does not match ARTIST and ALBUM tags")
    if not 'DATE' in flacfile.comments \
       or not flacfile.comments['DATE'] \
       or flacfile.comments['DATE'] == 'None':
        msg(LV_WARN, 'missing or bogus DATE tag')
    if not 'OWNER' in flacfile.comments \
       or not flacfile.comments['OWNER']:
        msg(LV_DEBUG, 'missing or blank OWNER tag')

if (flacfile.total_samples % 588):
    msg(LV_ERROR, 'sample count not a multiple of 588, slimserver parser will barf')
