"""
Main flacenstein GUI form.  You probably don't want to run this module directly,
but rather start the program by running flacapp.py.  Was originally created
with wxGlade 0.3.4 but has been heavily modified since then.

Copyright (C) 2005 Michael A. Dickerson.  Modification and redistribution
are permitted under the terms of the GNU General Public License, version 2.
"""

import os
import pickle
import sys
import tempfile
import time
import wx

import flaccfg
import flaclib

xfmmod = None

ID_MINNUM     = 100
ID_OPEN       = 101
ID_SAVE       = 102
ID_SETPATH    = 103
ID_RESCAN     = 104
ID_SELECTALL  = 105
ID_SELECTNONE = 106
ID_LOADSELECT = 107
ID_SAVESELECT = 108
ID_CONFIGURE  = 109
ID_RIP        = 110
ID_STOP       = 111
ID_TIMER      = 112
ID_EXPORT     = 113
ID_MAXNUM     = 120

STATE_IDLE      = 0
STATE_ENCODING  = 1
STATE_CANCELLED = 2

class MainLibFrame(wx.Frame):

    def __init__(self, *args, **kwds):

        # begin wxGlade: MainLibFrame.__init__
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        # tell wx about our hard coded IDs so wx.NewId() doesn't collide
        # with them
        for i in range(ID_MINNUM, ID_MAXNUM): wx.RegisterId(i)
            
        # set up list control
        self.list = wx.ListView(self, -1, style=wx.LC_REPORT|wx.SUNKEN_BORDER)
        self.list.InsertColumn(0, "Artist", width=150)
        self.list.InsertColumn(1, "Album", width=350)
        self.list.InsertColumn(2, "Date", width=100)
        wx.EVT_LIST_COL_CLICK(self, -1, self.OnListSort)
        wx.EVT_LIST_ITEM_RIGHT_CLICK(self, -1, self.OnListClick)
        wx.EVT_LIST_ITEM_ACTIVATED(self, -1, self.OnListDoubleClick)
        wx.EVT_LIST_ITEM_FOCUSED(self, -1, self.OnListSelect)

        # set up controls in properties panel
        self.bmpCoverArt = wx.StaticBitmap(self, -1)
        self.lblArtist = wx.StaticText(self, -1, "Welcome to Flacenstein")
        self.lblAlbum = wx.StaticText(self, -1,
                                      "Right click to select library items")
        self.ggeProgress = wx.Gauge(self, -1, 1)
        
        # Menu Bar
        self.library_menubar = wx.MenuBar()
        self.SetMenuBar(self.library_menubar)
        wxglade_tmp_menu = wx.Menu()
        wxglade_tmp_menu.Append(ID_OPEN, "Load Library\tCTRL-O", "",
                                wx.ITEM_NORMAL)
        wxglade_tmp_menu.Append(ID_SAVE, "Save Library\tCTRL-S", "",
                                wx.ITEM_NORMAL)
        wxglade_tmp_menu.Append(ID_EXPORT, "Export List", "", wx.ITEM_NORMAL)
        wxglade_tmp_menu.AppendSeparator()
        wxglade_tmp_menu.Append(ID_SETPATH, "Configure Paths", "", wx.ITEM_NORMAL)
        wxglade_tmp_menu.Append(ID_RESCAN, "Rescan\tF5", "", wx.ITEM_NORMAL)
        wxglade_tmp_menu.AppendSeparator()
        wxglade_tmp_menu.Append(ID_RIP, "Rip...", "", wx.ITEM_NORMAL)
        wxglade_tmp_menu.AppendSeparator()
        wxglade_tmp_menu.Append(wx.ID_EXIT, "Quit\tCTRL-Q", "", wx.ITEM_NORMAL)
        self.library_menubar.Append(wxglade_tmp_menu, "Library")

        wxglade_tmp_menu = wx.Menu()
        wxglade_tmp_menu.Append(ID_LOADSELECT, "Load Selection\tCTRL-G", "",
                                wx.ITEM_NORMAL)
        wxglade_tmp_menu.Append(ID_SAVESELECT, "Save Selection\tCTRL-D", "",
                                wx.ITEM_NORMAL)
        wxglade_tmp_menu.AppendSeparator()
        wxglade_tmp_menu.Append(ID_SELECTALL, "All\tCTRL-A", "", wx.ITEM_NORMAL)
        wxglade_tmp_menu.Append(ID_SELECTNONE, "None", "", wx.ITEM_NORMAL)
        self.library_menubar.Append(wxglade_tmp_menu, "Select")

        tmp_menu = wx.Menu()
        tmp_menu.Append(ID_CONFIGURE, "Configure", "", wx.ITEM_NORMAL)
        # mnuStop has to be explicitly created so that we can call .Enable()
        self.mnuStop = wx.MenuItem(tmp_menu, ID_STOP, "Stop", "",
                                   wx.ITEM_NORMAL)
        tmp_menu.AppendItem(self.mnuStop)
        tmp_menu.AppendSeparator()
        
        self.transforms = { }
        for xfm in flaccfg.XFM_MODS:
            global xfmmod
            xfmmod = __import__('flacenstein.xfm%s' % xfm, globals(),
                                locals(), 'xfm%s' % xfm)
            i = wx.NewId()
            self.transforms[i] = xfm
            tmp_menu.Append(i, xfmmod.description, "", wx.ITEM_NORMAL)
            works = xfmmod.ready()
            tmp_menu.Enable(i, works)
            if not works:
                print '"%s" module failed self-tests and is disabled.' % \
                    xfmmod.description
            wx.EVT_MENU(self, i, self.OnTransform)
            del xfmmod

        self.library_menubar.Append(tmp_menu, "Transform")

        wx.EVT_MENU(self, ID_OPEN,       self.OnOpen)
        wx.EVT_MENU(self, ID_SAVE,       self.OnSave)
        wx.EVT_MENU(self, ID_EXPORT,     self.OnExport)
        wx.EVT_MENU(self, ID_SETPATH,    self.OnSetPath)
        wx.EVT_MENU(self, ID_RESCAN,     self.OnRescan)
        wx.EVT_MENU(self, wx.ID_EXIT,    self.OnQuit)
        wx.EVT_MENU(self, ID_SELECTALL,  self.OnSelectAll)
        wx.EVT_MENU(self, ID_SELECTNONE, self.OnSelectNone)
        wx.EVT_MENU(self, ID_LOADSELECT, self.OnLoadSelection)
        wx.EVT_MENU(self, ID_SAVESELECT, self.OnSaveSelection)
        wx.EVT_MENU(self, ID_CONFIGURE,  self.OnConfigure)
        wx.EVT_MENU(self, ID_STOP,       self.OnStop)
        wx.EVT_MENU(self, ID_RIP,        self.OnRip)
        # Menu Bar end

        self.library_statusbar = self.CreateStatusBar(1, 0)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        # horrible kludge to try to work around the fact that on my home
        # machine, e.RequestMore(True) in an idle handler appears to do
        # nothing: idle events stop coming in if you don't move the mouse,
        # etc.
        self.timer = wx.Timer(self, ID_TIMER)
        wx.EVT_TIMER(self, ID_TIMER, self.OnIdle)
        #wx.EVT_IDLE(self, self.OnIdle)
        
        self.listdict = { }
        self.sortfields = ["artist", "date"]
        self.savefile = "flaclibrary.dat"
        self.listfile = "flacselection.lst"
        self.outpath  = "/tmp/flac"
        self.parallelism = flaccfg.DEFAULT_PARALLELISM
        self.children = { }
        self.jobs = []
        self.workinprogress = False
        self.mnuStop.Enable(False)

        self.lib = flaclib.FlacLibrary("/mnt/flac")
        self.lib.statusnotify = self.statusNotify        
        if os.path.isfile(flaccfg.DEFAULT_LIBRARY):
            self.loadLibrary(flaccfg.DEFAULT_LIBRARY)
        else:
            self.lib.scan()
            self.displayLibrary()
        
        self.setState(STATE_IDLE)
        
    def __set_properties(self):
        # begin wxGlade: MainLibFrame.__set_properties
        self.SetTitle("Flacenstein")
        self.SetSize((640, 480))
        self.list.SetFont(wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        self.library_statusbar.SetStatusWidths([-1])
        self.bmpCoverArt.SetSize((120, 120))
        self.lblArtist.SetSize((300, 25))
        self.lblAlbum.SetSize((300, 25))
        self.ggeProgress.SetSize((300, 25))
        # statusbar fields
        library_statusbar_fields = ["Ready"]
        for i in range(len(library_statusbar_fields)):
            self.library_statusbar.SetStatusText(library_statusbar_fields[i], i)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MainLibFrame.__do_layout
        sizPropLabels = wx.BoxSizer(wx.VERTICAL)
        sizPropLabels.Add(self.lblArtist, 0, wx.ALL, 5)
        sizPropLabels.Add(self.lblAlbum, 0, wx.ALL, 5)
        sizPropLabels.Add(self.ggeProgress, 0, wx.ALL|wx.FIXED_MINSIZE, 5)
        
        sizProperties = wx.BoxSizer(wx.HORIZONTAL)
        sizProperties.Add(self.bmpCoverArt, 0, wx.ALL|wx.FIXED_MINSIZE, 5)
        sizProperties.Add(sizPropLabels, 0, 0, 0)

        sizForm = wx.BoxSizer(wx.VERTICAL)
        sizForm.Add(sizProperties, 0, 0, 0)        
        sizForm.Add(self.list, 1, wx.EXPAND, 0)
        
        self.SetAutoLayout(1)
        self.SetSizer(sizForm)
        self.Layout()
        # end wxGlade

    def OnOpen(self, e):
        d = wx.FileDialog(self, "Open a FLAC library", os.getcwd(),
                          self.savefile, flaccfg.LIBFILE_FILTER, wx.OPEN)
        if d.ShowModal() == wx.ID_OK:
            self.loadLibrary(os.path.join(d.GetDirectory(), d.GetFilename()))
        d.Destroy()
        self.displayLibrary()
        
    def OnSave(self, e):
        d = wx.FileDialog(self, "Save FLAC library", os.getcwd(),
                          self.savefile, flaccfg.LIBFILE_FILTER, wx.SAVE)
        if d.ShowModal() == wx.ID_OK:
            self.saveLibrary(os.path.join(d.GetDirectory(), d.GetFilename()))
        d.Destroy()

    def OnExport(self, e):
        d = wx.FileDialog(self, "Export text list", os.getcwd(),
                          "flac-library.txt", flaccfg.LISTFILE_FILTER, wx.SAVE)
        if d.ShowModal() == wx.ID_OK:
            f = open(os.path.join(d.GetDirectory(), d.GetFilename()), 'w')
            for flac in self.lib.flacs.values():
                try:
                  f.write("%-20.20s %-30.30s %-10.10s\n" \
                          % (flac.artist.encode('utf8'), 
                             flac.album.encode('utf8'),
                             flac.date))
                except:
                  print('Couldn\'t write album, probably '
                        'because of some Unicode bullshit.')
            f.close()
            #except:
            #    m = wx.MessageDialog(self, "Save failed for some reason",
            #                         "Save error", wx.OK | wx.ICON_ERROR)
            #    m.ShowModal()
            #    m.Destroy()
        return

    def OnSetPath(self, e):
        """Set the library root path(s), as understood by the FlacLibrary class."""
        import frmPaths
        f = frmPaths.frmPaths(self, -1, "Configure Paths")
        f.paths = self.lib.rootpaths
        f.displayPaths()
        f.ShowModal()
        self.lib.rootpaths = f.paths[:]
        f.Destroy()
        
    def OnRip(self, e):
        """
        Open the ripper form.  Once it is visible, it takes care of itself.
        """
        import ripper
        f = ripper.frmRipper(self, -1)
        # default output path is first entry in library root path list
        f.txtOutPath.SetValue(self.lib.rootpaths[0])
        f.Show(True)

    def OnRescan(self, e):
        self.lib.scan()
        self.displayLibrary()

    def OnQuit(self, e):
        self.saveLibrary(flaccfg.DEFAULT_LIBRARY)
        self.Close(True)

    def OnSelectAll(self, e):
        for f in self.lib.flacs.values():
            f.selected = True
        self.displayLibrary()

    def OnSelectNone(self, e):
        self.clearSelection()
        self.displayLibrary()
        
    def OnListSort(self, e):
        c = e.GetColumn()
        if (c == 0):
            self.sortfields = ["artist", "date", "album"]
        elif (c == 1):
            self.sortfields = ["album", "artist", "date"]
        elif (c == 2):
            self.sortfields = ["date", "artist", "album"]
        self.displayLibrary()

    def OnListClick(self, e):
        i = e.GetIndex()
        sel = not self.lib.flacs[self.listdict[i]].selected
        self.lib.flacs[self.listdict[i]].selected = sel
        if (sel):
            self.list.SetItemBackgroundColour(i, flaccfg.LIST_SELECTED_COLOR)
        else:
            self.list.SetItemBackgroundColour(i, flaccfg.LIST_UNSELECTED_COLOR)

    def OnListDoubleClick(self, e):
        i = e.GetIndex()
        import tageditor
        f = tageditor.frmTagEditor(self, -1)
        # default output path is first entry in library root path list
        f.SetFlac(self.lib.flacs[self.listdict[i]])
        f.Show(True)
        
    def OnListSelect(self, e):
        i = e.GetIndex()
        if i > -1:
            flac = self.lib.flacs[self.listdict[i]]
            self.displayFlac(flac)
        return

    def OnLoadSelection(self, e):
        """
        These babies will be on store shelves while he's still grappling
        with the pickle matrix.
        """
        d = wx.FileDialog(self, "Open a list file", os.getcwd(),
                          self.listfile, flaccfg.LISTFILE_FILTER, wx.OPEN)
        if d.ShowModal() == wx.ID_OK:
            self.listfile = os.path.join(d.GetDirectory(), d.GetFilename())
            f = open(self.listfile, "r")
            selectionlist = pickle.load(f)
            f.close()
            self.clearSelection()
            for k in selectionlist:
                if self.lib.flacs.has_key(k):
                    self.lib.flacs[k].selected = True
            self.displayLibrary()                    
        d.Destroy()

    def OnSaveSelection(self, e):
        """MMMHOOOOYVEN GEE"""
        d = wx.FileDialog(self, "Save selections to list file", os.getcwd(),
                          self.listfile, flaccfg.LISTFILE_FILTER, wx.SAVE)
        if d.ShowModal() == wx.ID_OK:
            selectionlist = [f.md5 for f in self.lib.flacs.values() if f.selected]
            self.listfile = os.path.join(d.GetDirectory(), d.GetFilename())
            f = open(self.listfile, "w")
            pickle.dump(selectionlist, f, pickle.HIGHEST_PROTOCOL)
            f.close()
        d.Destroy()

    def OnTransform(self, e):
        i = e.GetId()
        #print "Initiating transform %d" % i
        #print "xfmmod.description is", xfmmod.description
        print "importing", self.transforms[i]
        global xfmmod
        xfmmod = __import__('flacenstein.'+self.transforms[i], globals(), locals(), \
                            [self.transforms[i]])
        print "xfmmod.description is", xfmmod.description
        #xfmmod.notify = self.statusNotify
        xfmmod.outpath = self.outpath
        if not xfmmod.ready():
            self.statusNotify("Transform module failed.")
            return

        class EncodeJob:
            """
            an empty container for holding the various data needed to
            tell an encoder what to do
            """
            pass

        artdir = tempfile.mkdtemp("", "flacart.")

        # The strategy here is to make up a queue of jobs to do, then register
        # a processing function as an idle event handler.  This lets the GUI
        # keep itself updated while the transformation is running.
        
        self.statusNotify("Preparing job list...")
        for f in self.lib.flacs.values():
            if f.selected:
                c = 0
                for t in f.tracks:
                    c += 1
                    j = EncodeJob()
                    j.artist = f.artist
                    if t: j.title = t
                    else: j.title = "Track %d" % c
                    j.album = f.album
                    j.tracknum = c
                    j.flacfile = f.filename
                    j.coverart = f.extractThumbnail(artdir)
                    j.listindex = f.listindex
                    fname = "%02d - %s.%s" % (c, t, xfmmod.extension)
                    j.outfile = os.path.join(self.outpath,
                                             flaclib.filequote(f.artist),
                                             flaclib.filequote(f.album),
                                             flaclib.filequote(fname))
                    j.failures = 0
                    # skip this job if outfile already exists
                    # (should probably compare modification times of output file
                    # and flac file)
                    if not os.path.isfile(j.outfile): self.jobs.append(j)
                    
        print "Prepared %d jobs" % len(self.jobs)
        # 18 Feb 05 MAD: the order is always surprising anyway
        #self.jobs.reverse() # so that we can pop() them in an unsurprising order
        self.maxjobs = len(self.jobs)
        self.ggeProgress.SetRange(self.maxjobs)
        self.lblArtist.SetLabel("Encoding in %d thread(s)" % \
                                self.parallelism)
        self.setState(STATE_ENCODING) # makes OnIdle() kick in
        self.statusNotify("Transformation in progress")
        return

    def OnIdle(self, e):
        """
        this method is now kind of misnamed, since it's not being run as
        an idle handler but rather fired from a timer.
        """
        if self.state == STATE_IDLE: return
        elif self.state == STATE_CANCELLED: self.jobs = []

        global xfmmod

        # if we have jobs to do, and empty child slots, fork a child
        if self.jobs and len(self.children.keys()) < self.parallelism:
            j = self.jobs.pop()
            self.lblAlbum.SetLabel(j.outfile)
            child = os.fork()
            if child == 0:
                # this is the child process; call the encodeFile() method
                # which should exec() an encoder process and exit with a
                # status code
                xfmmod.encodeFile(j)
                # if you ever get here, something went wrong
                sys.stderr.write('Whuh-oh, encodeFile() returned.\n')
                sys.exit(1)
            # this is the parent process; remember the job in a dictionary
            # and wait to see what happens
            self.list.SetItemBackgroundColour(j.listindex, "pink")
            self.children[child] = j
            jobsleft = len(self.jobs) + len(self.children.keys())
            self.ggeProgress.SetValue(self.maxjobs - jobsleft)

        # if we have children running, see if any have exited
        if self.children:
            exited, status = os.waitpid(-1, os.WNOHANG)
            if exited and self.children.has_key(exited):
                j = self.children[exited]
                if not os.WIFEXITED(status) or os.WEXITSTATUS(status):
                    j.failures += 1
                    if j.failures > 2:
                        print "%s - %s: Giving up." % (j.artist, j.title)
                    else:
                        print "%s - %s: Job failed, retrying" % (j.artist, j.title)
                        self.jobs.append(j)
                del self.children[exited]
            elif exited:
                print "Got unknown child PID %d, something's weird" % exited
            jobsleft = len(self.jobs) + len(self.children.keys())
            self.ggeProgress.SetValue(self.maxjobs - jobsleft)

        # if we have no jobs left and no children to wait for, we're done
        if not self.jobs and not self.children:
            self.statusNotify("Transform done.")
            xfmmod.cleanup()
            del xfmmod
            self.setState(STATE_IDLE)

        return
            
    def OnStop(self, e):
        """when the Stop menu item is clicked during a transform, stop
        gracefully by clearing the job queue and allowing the children to
        exit."""
        self.setState(STATE_CANCELLED)

    def OnConfigure(self, e):
        """TODO: make this a form with more options."""
        d = wx.DirDialog(self, "Choose plugin output path", self.outpath)
        if d.ShowModal() == wx.ID_OK:
            self.outpath = d.GetPath()
        
    def clearSelection(self):
        for f in self.lib.flacs.values():
            f.selected = False

    def loadLibrary(self, f):
        """
        Load a stored library from a file.  A stored library is a pickled
        list of FlacFile instances.  Note that the FlacLibrary instance itself
        can't be pickled, because it contains a member that is a function.
        """
        try:
            self.lib.flacs, self.lib.rootpaths, self.outpath = \
                flaclib.loadSavefile(f)
            self.savefile = f
            self.displayLibrary()
        except:
            m = wx.MessageDialog(self,
                                 "Load failed; save file appears to be bogus.",
                                 "Load error",
                                 wx.OK | wx.ICON_ERROR)
            m.ShowModal()
            m.Destroy()
        return

    def saveLibrary(self, f):
        """Pickles the list of FlacFile instances to a file."""
        try:
            flaclib.writeSavefile(f, self.lib.flacs, self.lib.rootpaths,
                                  self.outpath)
            self.savefile = f
        except:
            m = wx.MessageDialog(self, "Save failed for some reason",
                                 "Save error", wx.OK | wx.ICON_ERROR)
            m.ShowModal()
            m.Destroy()
        return
        
    def displayLibrary(self):
        """Redraws list control using the self.lib object for state
        infomrmation"""
        def flaccmp(a,  b):
            """A throwaway list sorting function"""
            for f in self.sortfields:
                c = cmp(self.lib.flacs[a].__dict__[f],
                        self.lib.flacs[b].__dict__[f])
                if (c != 0):
                    return c
            return 0
                
        sorted = self.lib.flacs.keys()                
        sorted.sort(flaccmp)
        
        self.list.DeleteAllItems()
        self.listdict.clear()
        c = 0
        for k in sorted:
            self.listdict[c] = k
            f = self.lib.flacs[k]
            f.listindex = c
            self.list.InsertStringItem(c, f.artist)
            self.list.SetStringItem(c, 1, f.album)
            if isinstance(f.date, str):
                self.list.SetStringItem(c, 2, f.date)
            if f.selected:
                self.list.SetItemBackgroundColour(c, "grey")
                #(c, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
            c += 1

    def statusNotify(self, msg):
        self.library_statusbar.SetStatusText(msg, 0)
        self.library_statusbar.Refresh()
        self.library_statusbar.Update()
        self.Refresh() # no-ops?
        self.Update()  # 

    def setState(self, newstate):
        self.state = newstate
        if newstate == STATE_IDLE:
            self.mnuStop.Enable(False)
            self.ggeProgress.SetValue(0)
            self.timer.Stop()
        elif newstate == STATE_ENCODING:
            self.mnuStop.Enable(True)
            self.timer.Start(500, wx.TIMER_CONTINUOUS)
        elif newstate == STATE_CANCELLED:
            self.mnuStop.Enable(False)                             
        else:
            print "internal error: setState() called with bad value"
        return

    def displayFlac(self, flac):
        self.lblArtist.SetLabel(flac.artist)
        if flac.date:
            self.lblAlbum.SetLabel("%s (%s)" % (flac.album, flac.date))
        else:
            self.lblAlbum.SetLabel(flac.album)
        imgfile = flac.extractThumbnail(flaccfg.IMAGE_TEMP_PATH)
        if imgfile:
            try:
                img = wx.Image(imgfile, wx.BITMAP_TYPE_ANY)
                img.Rescale(120, 120)
                self.bmpCoverArt.SetBitmap(wx.BitmapFromImage(img))
            except:
                print "error loading cover art thumbnail"
                self.bmpCoverArt.SetBitmap(wx.Bitmap(flaccfg.MISSING_ART_IMAGE))
        else:
            self.bmpCoverArt.SetBitmap(wx.Bitmap(flaccfg.MISSING_ART_IMAGE))
        return

# end of class MainLibFrame

if __name__ == '__main__':
    print 'You didn\'t mean to execute this module.  To start Flacenstein,'
    print 'run flacapp.py.'
    
