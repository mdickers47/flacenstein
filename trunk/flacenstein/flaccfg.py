"""
This configuration file happens to be Python code that is executed
near the start of the Flacenstein program.
"""

# Filename filters displayed when opening or saving libraries or selections
LISTFILE_FILTER = "List files (*.lst)|*.lst|All files (*)|*"
LIBFILE_FILTER  = "Data files (*.dat)|*.dat|All files (*)|*"
LISTFILE_FILTER = "Text files (*.txt)|*.txt|All files (*)|*"

# If the file DEFAULT_LIBRARY exists, it will be automatically opened when
# Flacenstein starts.  If the file DEFAULT_LIBRARY is writable, the current
# library will automatically be saved there when Flacenstein exits.
DEFAULT_LIBRARY = "~/.flacenstein-library"

# the background colors for selected and unselected rows in the flac table
LIST_SELECTED_COLOR = "grey"
LIST_UNSELECTED_COLOR = "white"

# when thumbnails are extracted from FLAC files for display, they will be
# stored in this path
IMAGE_TEMP_PATH = "/tmp/flac"
MISSING_ART_IMAGE = "~/build/flacenstein/flacenstein/colorfulcd.jpg"

# when transforming (encoding from FLAC to something else), this many
# processes will be run simultaneously
DEFAULT_PARALLELISM = 1

# how to execute various needed binaries
BIN_FLAC = 'flac'
BIN_METAFLAC = 'metaflac'
BIN_LAME = 'lame'
BIN_CDPARANOIA = 'cdparanoia'

# there should be a python module 'xfm%s.py' for each entry here
XFM_MODS = ('aac', 'vorbis', 'mp3', 'mp3_art')
