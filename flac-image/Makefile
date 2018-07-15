# Not much to see here, but this is enough for "make" to produce a flac-image
# binary.  If your FLAC headers are not in a path that the C compiler searches
# by default, you probably need to add -I/usr/whereever/flac to CFLAGS and
# -L/usr/lib/whereever to the link step.

CFLAGS=-Wall -g -I/opt/local/include -L/opt/local/lib

flac-image: flac-image.o
	gcc -o flac-image -lFLAC flac-image.o -L/opt/local/lib

clean:
	rm -f flac-image flac-image.o

install:
	install -d $(DESTDIR)/usr/bin
	install flac-image $(DESTDIR)/usr/bin
	install -d $(DESTDIR)/usr/share/man/man1
	install flac-image.1 $(DESTDIR)/usr/share/man/man1
	gzip -9 $(DESTDIR)/usr/share/man/man1/flac-image.1

uninstall:
	rm -f $(DESTDIR)/usr/bin/flac-image $(DESTDIR)/usr/man/man1/flac-image.*

dist:
	tar -C .. -czf flac-image_1.0.tar.gz flac-image
