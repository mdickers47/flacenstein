#!/usr/bin/python
"""
Flacenstein "launcher" script.  This is what you generally want to run to
start the program, e.g. 'python flacapp.py'.

Copyright (C) 2005 Michael A. Dickerson.  Modification and redistribution
are permitted under the terms of the GNU General Public License, version 2.
"""

import wxversion
wxversion.select('3.0')

import os
import sys
import wx

import flacenstein.flaclib as flaclib
import flacenstein.flaccfg as flaccfg

cfgfile = os.path.expanduser("~/.flacensteinrc")
if os.path.isfile(cfgfile):
    import cfgfile as flaccfg

# give file parameters the benefit of ~ expansion
flaccfg.DEFAULT_LIBRARY = os.path.expanduser(flaccfg.DEFAULT_LIBRARY)
flaccfg.IMAGE_TEMP_PATH = os.path.expanduser(flaccfg.IMAGE_TEMP_PATH)
flaccfg.MISSING_ART_IMAGE = os.path.expanduser(flaccfg.MISSING_ART_IMAGE)

app = wx.PySimpleApp()
if len(sys.argv) > 1 and sys.argv[1].endswith("rip"):
    from flacenstein import ripper
    f = ripper.frmRipper(None, -1, "Flacenstein Ripper")
    if len(sys.argv) > 2:
        f.cddevice = sys.argv[2]
else:
    import flacenstein.mainframe as mainframe
    f = mainframe.MainLibFrame(None, -1, "Flacenstein")
f.Show(1)
app.MainLoop()

print "See You Space Cowboy"
