"""
Just enough support code to call Amazon Web Services (now known as ECS
or something).  Note that you can't do this without a subscription
ID.  I am leaving my own hard coded here, since I think I am allowed
to do that, but the Amazon license is not exactly light reading.  You
can always get your own, you just have to fill out some forms and
crap.  Please get your own if you reuse this code in some other
program that is not Flacenstein, or if you are looking up hundreds of
CDs a day.

Copyright (C) 2005 Michael A. Dickerson.  Modification and
redistribution are permitted under the terms of the GNU General Public
License, version 2.
"""

# 29 Jan 05 MAD: IT WORKS! THE REBIGULATOR WORKS!

import urllib
import xml.sax

SUBSCRIPTION_ID = "15W83BT1GBHQK5BK1K82"

def SearchForCoverArt(artist, title):
    """
    Given an artist and album name in string form, returns a tuple of
    disc release date followed by a list of image URLs.
    """
    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_namespaces, False)
    
    url = "http://webservices.amazon.com/onca/xml?"
    url += urllib.urlencode({'Service': 'AWSECommerceService',
                             'SubscriptionId': SUBSCRIPTION_ID,
                             'Operation': 'ItemSearch',
                             'Artist': artist.encode('utf-8'),
                             'Title': title.encode('utf-8'),
                             'SearchIndex': 'Music'})
    doc = urllib.urlopen(url)
    handler = ASINHandler()
    parser.setContentHandler(handler)
    parser.parse(doc)
    items = handler.asins[:]
    images = []
    date = None
    
    for item in items:
        url = "http://webservices.amazon.com/onca/xml?" \
              + "Service=AWSECommerceService" \
              + "&SubscriptionId=" + SUBSCRIPTION_ID \
              + "&Operation=ItemLookup" \
              + "&ResponseGroup=ItemAttributes,Images" \
              + "&ItemId=" + item
        doc = urllib.urlopen(url)
        handler = ImageURLHandler()
        parser.setContentHandler(handler)
        parser.parse(doc)
        if handler.url: images.append(handler.url)
        if handler.releasedate: date = handler.releasedate
        
    return (date, images)
    
class ASINHandler(xml.sax.handler.ContentHandler):
    """
    I hate this crap.  If I wanted to write a class implementing four
    interfaces and two dozen callbacks for every simple operation, I would
    be using Java.
    """

    def __init__(self):
        self.asins = []
        self.inASIN = False
        self.buff = ""
        
    def error(self, e): print "xml error: %s" % e
    
    def startElement(self, name, attrs):
        if name == 'ASIN': self.inASIN = True
    
    def characters(self, ch):
        if self.inASIN: self.buff += ch
        
    def endElement(self, name):
        if name == 'ASIN':
            self.asins.append(self.buff)
            self.buff = ""
            self.inASIN = False
            

class ImageURLHandler(xml.sax.handler.ContentHandler):
    """
    This handler selects the largest image in the document and saves
    its URL as the url attribute.  Also remembers the ReleaseDate product
    attribute if one was found.
    """

    def __init__(self):
        # these are the attributes you should look at
        self.url = None
        self.releasedate = None

        self.largestH = 0
        self.largestW = 0
        self.inImage = False
        self.thisH = 0
        self.thisW = 0
        self.thisURL = ""
        self.buff = ""

    def error(self, e): print "xml error: %s" % e

    def startElement(self, name, attrs):
        if name.find('Image') > 0: self.inImage = True

    def characters(self, ch): self.buff += ch
    
    def endElement(self, name):
        if self.inImage:
            if name =='URL':
                self.thisURL = self.buff
                self.buff = ""
            elif name == 'Height':
                self.thisH = int(self.buff)
                self.buff = ""
            elif name == 'Width':
                self.thisW = int(self.buff)
                self.buff = ""
            elif name.find('Image') > 0:
                # we just aren't going to worry about what happens if
                # we try to compare images with different aspect ratios
                if self.thisH > self.largestH or self.thisW > self.largestW:
                    self.largestH = self.thisH
                    self.largestW = self.thisW
                    self.url = self.thisURL
                self.inImage = False
        elif name == 'ReleaseDate':
            self.releasedate = self.buff
        else:
            self.buff = "" # might as well not waste memory
                    
            
          
    
