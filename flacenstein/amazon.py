#!/usr/bin/python
"""
Just enough support code to call Amazon Web Services (now known as ECS
or something).

Unfortunately, as of August 2009, all AWS requests must be signed with a
AWSAccessKeyId and matching secret key.  So I can't hard-code my own
'subscription id' anymore and just have it work for everybody.  You can get
your own account here:

http://docs.amazonwebservices.com/AWSEcommerceService/4-0/

After that, create a file in /etc/s3_keys or ~/.s3_keys that contains
AWSAccessKeyId on line 1 and secret key on line 2.

Copyright (C) 2005-2011 Michael A. Dickerson.  Modification and
redistribution are permitted under the terms of the GNU General Public
License, version 2.
"""

import base64
import hashlib
import hmac
import os
import time
import urllib
import xml.sax

class NoAmazonKeys (Exception): pass

AMAZON_HOST = 'webservices.amazon.com'
AMAZON_KEYS = None

def _GetAmazonKeys():
    global AMAZON_KEYS
    if AMAZON_KEYS: return AMAZON_KEYS
    for p in ['~/.s3_keys', '/etc/s3_keys']:
        p = os.path.expanduser(p)
        if os.path.exists(p):
            AMAZON_KEYS = [x.strip() for x in open(p, 'r').readlines()]
            return AMAZON_KEYS
    raise NoAmazonKeys


def _urlencode_right(d):
    """
    Sigh.  urllib.urlencode() uses quote_plus internally, which makes
    'Johnny Depp' into 'Johnny+Depp' instead of 'Johnny%20Depp'.  This
    ruins the signature.  So we have to do it ourselves.
    """
    quoted_params = ['%s=%s' % (key, urllib.quote(val, safe='')) \
                      for (key, val) in sorted(d.items())]
    return '&'.join(quoted_params)


def _MakeAmazonUrl(d):
    d.setdefault('Service', 'AWSECommerceService')
    # NB: I include an associate tag because the API fails without it.  It
    # makes no difference because there is no means of buying the CD from
    # flacenstein, and the tag actually doesn't even work anymore.
    d.setdefault('AssociateTag', 'singingtree-20')
    d.setdefault('AWSAccessKeyId', _GetAmazonKeys()[0])
    d.setdefault('Timestamp', time.strftime('%Y-%m-%dT%H:%M:%SZ', 
                                            time.gmtime()))
    canonical_str = _urlencode_right(d)
    #print 'canonical_str:\n', canonical_str
    sign = 'GET\n' + AMAZON_HOST + '\n/onca/xml\n' + canonical_str
    #print 'string to sign:\n', sign
    #print 'secret key is: %s' % _GetAmazonKeys()[1]
    sign = hmac.new(_GetAmazonKeys()[1], sign, hashlib.sha256)
    sign = base64.encodestring(sign.digest()).strip()
    #print 'signature:\n', sign

    d['Signature'] = sign
    url = 'http://' + AMAZON_HOST + '/onca/xml?'
    url += _urlencode_right(d)

    #print 'url:', url
    return url


def LookupDisc(artist, title):
    """
    Given an artist and album name in string form, returns a tuple of
    disc release date followed by a list of image URLs.

    Raises NoAmazonKeys if we aren't configured to do amazon searches.
    """
    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_namespaces, False)

    url = _MakeAmazonUrl({'Operation': 'ItemSearch',
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
        url = _MakeAmazonUrl({'Operation': 'ItemLookup',
                              'ResponseGroup': 'ItemAttributes,Images',
                              'ItemId': item})
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


if __name__ == '__main__':
    """
    validate url-signing code against the examples at:
    http://docs.amazonwebservices.com/AWSECommerceService/latest/DG/index.html?rest-signature.htm
    """
    # Note no 'global' here because we are not inside any function.
    AMAZON_KEYS = ['00000000000000000000', '1234567890']
    AMAZON_HOST = 'ecs.amazonaws.co.uk'
    url = _MakeAmazonUrl({'Operation': 'ItemSearch',
                          'Actor': 'Johnny Depp',
                          'ResponseGroup': ('ItemAttributes,Offers,Images,'
                                            'Reviews,Variations'),
                          'Version': '2009-01-01',
                          'SearchIndex': 'DVD',
                          'Sort': 'salesrank',
                          'AssociateTag': 'mytag-20',
                          'Timestamp': '2009-01-01T12:00:00Z'})
    correct = ('http://ecs.amazonaws.co.uk/onca/xml?'
               'AWSAccessKeyId=00000000000000000000&Actor=Johnny%20Depp'
               '&AssociateTag=mytag-20&Operation=ItemSearch&'
               'ResponseGroup=ItemAttributes%2COffers%2CImages%2CReviews'
               '%2CVariations&SearchIndex=DVD&Service=AWSECommerceService'
               '&Signature=TuM6E5L9u%2FuNqOX09ET03BXVmHLVFfJIna5cxXuHxiU%3D'
               '&Sort=salesrank&Timestamp=2009-01-01T12%3A00%3A00Z'
               '&Version=2009-01-01')
    assert url == correct

    AMAZON_HOST = 'ecs.amazonaws.jp'
    url = _MakeAmazonUrl({'Operation': 'ListSearch',
                          'Version': '2009-01-01',
                          'ListType': 'WishList',
                          'Name': 'wu',
                          'AssociateTag': 'mytag-20',
                          'Timestamp': '2009-01-01T12:00:00Z'})
    correct=('http://ecs.amazonaws.jp/onca/xml?AWSAccessKeyId=00000000000000000'
             '000&AssociateTag=mytag-20&ListType=WishList&Name=wu&Operation=Lis'
             'tSearch&Service=AWSECommerceService&Signature=aMFgBNKPrz9PRR9Ato7'
             'yanlaG%2FPkQsNxIWYbLD1V9Zc%3D&Timestamp=2009-01-01T12%3A00%3A00Z&'
             'Version=2009-01-01')
    assert url == correct

    print 'self-test OK!'


