#!/usr/bin/perl
#
# Script to transcode (convert) an entire directory tree
# from .mp3 to AAC .m4a.  Yes I know this is a very lossy
# process, but my source mp3s are pretty good to begin with
# (LAME vbr ~192-224kbps), and AAC saves so much space that
# this way I can fit twice as much on the iPod.
#
# All the filename mangling assumes that you use the script
# in exactly this way: cd to the directory CONTAINING the
# directory you want to transcode, then call the script with
# the name of that directory.  For example, if you want to
# transcode /mnt/share/new:
#
# $ cd /mnt/share
# $ ~/transcode.pl new
#
# This will create /mnt/share/new-xc which mirrors
# /mnt/share/new but has an m4a in place of each mp3.
#
# Written 30 Nov 04 by M. Dickerson

use strict;
use warnings;
use MP3::Info;

# You will need all of the following programs:
my $FAAC = "/usr/local/bin/faac";
my $MADPLAY = "/usr/bin/madplay";

die "Required program missing"
    unless (-x $FAAC && -x $MADPLAY);
 
my $basepath = $ARGV[0];
my $subst = "s/$basepath/$basepath-xc/";
print "Searching $basepath\nRegex is $subst\n";

open FIND, "find $basepath -type f |";

while (<FIND>)
{
    # cheesy `basename`-like trick
    $_ =~ /^(.*)\/(.*?)$/;
    my ($path, $fname) = ($1, $2);
    my ($newpath, $newname) = ($path, $fname);
    $newpath =~ s/$basepath/${basepath}-xc/;
    $newname =~ s/.mp3$/.m4a/;

    &syscmd("mkdir -p $newpath") unless (-d $newpath);
    if ($fname =~ /.mp3$/i) {
	print "=> Transcoding $fname\n";
	if (-f "$newpath/$newname") {
	    print "(skipping, already done)\n";
	    next;
	}
	my $id3 = &get_mp3tag("$path/$fname");
	# have to escape 's in file names
	my $in = &quote("$path/$fname");
	my $out = &quote("$newpath/$newname");
	my $faac = "$FAAC -o $out"
	    . " --artist " . &quote($id3->{ARTIST})
	    . " --title "  . &quote($id3->{TITLE})
	    . " --genre "  . &quote($id3->{GENRE})
	    . " --album "  . &quote($id3->{ALBUM})
	    . " --track "  . &quote($id3->{TRACKNUM})
	    . " --comment 'Transcoded from MP3' "
	    . " -";
	&syscmd("$MADPLAY -o wave:- $in | $faac");
    } else {
	print "=> Copying $fname\n";
	if (-f "$newpath/$fname") {
	    print "(skipping, already done)\n";
	    next;
	}
	&syscmd("cp $path/$fname $newpath/$fname");
    }
}

sub syscmd()
{
    # when testing, its a good idea to print commands
    # instead of run them..
    print "RUNNING: @_\n";
    system(@_);
}

sub quote()
{
    (my $x) =  @_;
    $x =~ s/"/\\"/g;
    $x = "\"$x\"";
    return $x;
}
