import os, sys, urllib, urllib2

new_path = [ os.path.join( os.path.dirname( __file__ ), '..', '..', '..', '..', 'lib' ) ]
new_path.extend( sys.path[ 1: ] )
sys.path = new_path

from galaxy import eggs
import pkg_resources

pkg_resources.require( "simplejson" )
import simplejson

pkg_resources.require( "pycrypto" )
from Crypto.Cipher import Blowfish
from Crypto.Util.randpool import RandomPool
from Crypto.Util import number

def encode_id( config_id_secret, obj_id ):
    # Utility method to encode ID's
    id_cipher = Blowfish.new( config_id_secret )
    # Convert to string
    s = str( obj_id )
    # Pad to a multiple of 8 with leading "!"
    s = ( "!" * ( 8 - len(s) % 8 ) ) + s
    # Encrypt
    return id_cipher.encrypt( s ).encode( 'hex' )

def delete( api_key, url, data, return_formatted=True ):
    # Sends an API DELETE request and acts as a generic formatter for the JSON response - 'data' will become the JSON payload read by Galaxy.
    try:
        url = make_url( api_key, url )
        req = urllib2.Request( url, headers = { 'Content-Type': 'application/json' }, data = simplejson.dumps( data ))
        req.get_method = lambda: 'DELETE'
        r = simplejson.loads( urllib2.urlopen( req ).read() )
    except urllib2.HTTPError, e:
        if return_formatted:
            print e
            print e.read( 1024 )
            sys.exit( 1 )
        else:
            return 'Error. '+ str( e.read( 1024 ) )
    if not return_formatted:
        return r
    print 'Response'
    print '--------'
    print r

def display( url, api_key=None, return_formatted=True ):
    # Sends an API GET request and acts as a generic formatter for the JSON response.
    try:
        r = get( url, api_key=api_key )
    except urllib2.HTTPError, e:
        print e
        print e.read( 1024 ) # Only return the first 1K of errors.
        sys.exit( 1 )
    if type( r ) == unicode:
        print 'error: %s' % r
        return None
    if not return_formatted:
        return r
    elif type( r ) == list:
        # Response is a collection as defined in the REST style.
        print 'Collection Members'
        print '------------------'
        for n, i in enumerate(r):
            # All collection members should have a name and url in the response.
            print '#%d: %s' % (n+1, i.pop( 'url' ) )
            if 'name' in i:
                print '  name: %s' % i.pop( 'name' )
            for k, v in i.items():
                print '  %s: %s' % ( k, v )
        print ''
        print '%d element(s) in collection' % len( r )
    elif type( r ) == dict:
        # Response is an element as defined in the REST style.
        print 'Member Information'
        print '------------------'
        for k, v in r.items():
            print '%s: %s' % ( k, v )
    elif type( r ) == str:
        print r
    else:
        print 'response is unknown type: %s' % type( r )

def get( url, api_key=None ):
    # Do the actual GET.
    url = make_url( url, api_key=api_key )
    try:
        return simplejson.loads( urllib2.urlopen( url ).read() )
    except simplejson.decoder.JSONDecodeError, e:
        print "URL did not return JSON data"
        sys.exit(1)

def make_url( url, api_key=None, args=None ):
    # Adds the API Key to the URL if it's not already there.
    if args is None:
        args = []
    argsep = '&'
    if '?' not in url:
        argsep = '?'
    if api_key:
        if '?key=' not in url and '&key=' not in url:
            args.insert( 0, ( 'key', api_key ) )
    return url + argsep + '&'.join( [ '='.join( t ) for t in args ] )

def post( url, data, api_key=None ):
    # Do the actual POST.
    url = make_url( url, api_key=api_key )
    req = urllib2.Request( url, headers = { 'Content-Type': 'application/json' }, data = simplejson.dumps( data ) )
    return simplejson.loads( urllib2.urlopen( req ).read() )

def put( url, data, api_key=None ):
    # Do the actual PUT.
    url = make_url( url, api_key=api_key )
    req = urllib2.Request( url, headers = { 'Content-Type': 'application/json' }, data = simplejson.dumps( data ))
    req.get_method = lambda: 'PUT'
    return simplejson.loads( urllib2.urlopen( req ).read() )

def submit( url, data, api_key=None, return_formatted=True ):
    # Sends an API POST request and acts as a generic formatter for the JSON response - 'data' will become the JSON payload read by Galaxy.
    try:
        r = post( url, data, api_key=api_key )
    except urllib2.HTTPError, e:
        if return_formatted:
            print e
            print e.read( 1024 )
            sys.exit( 1 )
        else:
            return 'Error. '+ str( e.read( 1024 ) )
    if not return_formatted:
        return r
    print 'Response'
    print '--------'
    if type( r ) == list:
        # Currently the only implemented responses are lists of dicts, because submission creates some number of collection elements.
        for i in r:
            if type( i ) == dict:
                if 'url' in i:
                    print i.pop( 'url' )
                else:
                    print '----'
                if 'name' in i:
                    print '  name: %s' % i.pop( 'name' )
                for k, v in i.items():
                    print '  %s: %s' % ( k, v )
            else:
                print i
    else:
        print r

def update( api_key, url, data, return_formatted=True ):
    # Sends an API PUT request and acts as a generic formatter for the JSON response - 'data' will become the JSON payload read by Galaxy.
    try:
        r = put( api_key, url, data )
    except urllib2.HTTPError, e:
        if return_formatted:
            print e
            print e.read( 1024 )
            sys.exit( 1 )
        else:
            return 'Error. ' + str( e.read( 1024 ) )
    if not return_formatted:
        return r
    print 'Response'
    print '--------'
    print r
