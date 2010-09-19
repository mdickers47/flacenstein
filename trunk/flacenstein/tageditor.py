"""
GUI form for editing tags in the Vorbis comment block.
"""
import os
import wx

import flaccfg
import flaclib

ID_MINNUM = 100
ID_SAVE   = 101
ID_CANCEL = 102
# ...
ID_MAXNUM = 110

CMD_SIZE = (80,25)

class frmTagEditor(wx.Frame):

    def __init__(self, *args, **kwds):

        kwds['style'] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        # tell wx about our hard coded IDs so that wx.NewId() doesn't collide
        for i in range(ID_MINNUM, ID_MAXNUM): wx.RegisterId(i)

        self.lblFilename = wx.StaticText(self, -1, 'FLAC file name here')
        self.txtTags = wx.TextCtrl(self, -1, '', style=wx.TE_MULTILINE)
        self.cmdSave = wx.Button(self, ID_SAVE, 'Save')
        self.cmdCancel = wx.Button(self, ID_CANCEL, 'Cancel')
        
        self.__set_properties()
        self.__do_layout()

        wx.EVT_BUTTON(self, ID_SAVE, self.OnSave)
        wx.EVT_BUTTON(self, ID_CANCEL, self.OnCancel)

    def __set_properties(self):
        self.SetTitle("Tag Editor")
        self.SetSize((400,450))
        self.lblFilename.SetSize((375,25))
        self.txtTags.SetSize((375,430))
        self.cmdSave.SetSize(CMD_SIZE)
        self.cmdCancel.SetSize(CMD_SIZE)

    def __do_layout(self):
        sizButtons = wx.BoxSizer(wx.HORIZONTAL)
        sizButtons.Add(self.cmdCancel, 0, wx.ALL|wx.FIXED_MINSIZE, 5)
        sizButtons.Add(self.cmdSave, 0, wx.ALL|wx.FIXED_MINSIZE, 5)
        
        sizForm = wx.BoxSizer(wx.VERTICAL)
        sizForm.Add(self.lblFilename, 0, wx.ALL, 5)
        sizForm.Add(self.txtTags, 1, wx.ALL|wx.EXPAND, 5)
        sizForm.Add(sizButtons, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)

        self.SetAutoLayout(True)
        self.SetSizer(sizForm)
        #sizForm.Fit(self)
        #sizForm.SetSizeHints(self)
        self.Layout()

    def SetFlac(self, flac):
        """
        Displays the file name, extracts current tags and displays them
        in the box, and remembers the full path so that we can call metaflac
        on it later.
        """
        self.lblFilename.SetLabel(os.path.basename(flac.filename))
        # note that we just shell-quote the filename now, since that is how
        # we are going to want it every time we ask for it
        self.flacfile = flaclib.shellquote(flac.filename)
        cmd = '%s --export-tags-to=- %s' % (flaccfg.BIN_METAFLAC, self.flacfile)
        t = os.popen(cmd, 'r')
        tags = unicode(t.read(), 'utf8')
        self.txtTags.SetValue(tags)
        t.close()
        
#         chain = metadata.Chain()
#         chain.read(self.flacfile)
#         it = metadata.Iterator()
#         it.init(chain)
#         vc = None
#         tags = ''
#         while True:
#             if it.get_block_type == metadata.VORBIS_COMMENT:
#                 vc = metadata.VorbisComment(it.get_block())
#                 break
#             if not it.next():
#                 break
#         if vc:
#             for c in vc.comments:
#                 tags += '%s=%s\n' % (c, vc.comments[c])
#         self.txtTags.SetValue(tags)

    def OnSave(self, e):
        """
        Event handler for 'Save' button press.  Should write contents of text box to
        FLAC file, then destroy form.
        """
        cmd = '%s --remove-all-tags %s' % (flaccfg.BIN_METAFLAC, self.flacfile)
        os.system(cmd)
        cmd = '%s --import-tags-from=- %s' % (flaccfg.BIN_METAFLAC, self.flacfile)
        out = os.popen(cmd, 'w')
        out.write(self.txtTags.GetValue().encode('utf8'))
        out.close()
        self.Destroy()
        
    def OnCancel(self, e):
        """
        Event handler for 'Cancel' button press.  Should just destroy form.
        """
        self.Destroy() # goodbye cruel world
