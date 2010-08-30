#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Tracker client
# Author: ypod
# Date: Oct 2006
#


import urllib, os, sys, time, httplib2, simplejson


def debug(arg):
    pass
    #print arg
    
    
def usage():
    debug( "Usage: %s [HOSTNAME]" )
    debug( "HOSTNAME is the name of the host whose IP you are querying (optional). If not provided, the local IP will be advertised in a loop." )
    debug( "Press Ctrl+C to stop." )
    

def send_request(request_url, params):
    
    request_url = '%s?%s' % (request_url, urllib.urlencode(params))
    h = httplib2.Http(timeout=10)
    dic = {'error':'', 'response':{}, 'url':''}
    dic['url'] = request_url
    
    try:
        resp, content = h.request(request_url, "GET")
    except Exception, e:
        dic['error'] = '%s' % e
        debug('send_request connection: %s\nError: %s' % (request_url, e))
        return dic
    
    if resp.status == 200:
        try:
            response = simplejson.loads(content)    
            dic['response'] = response    
            
        except Exception, e:
            dic['error'] = '%s' % e
            debug('send_request: %s\nError: %s' % (request_url, e))
            
    else:
        dic['error'] = 'Status %s: %s' % (resp.status, content)
    
    return dic
    

HOSTNAME = os.popen("hostname").readlines()[0].strip()
SERVER_URL = 'http://tagnet.media.mit.edu/ypod/iptracker'


if __name__=='__main__':
    
    if len(sys.argv) > 1:
        params = {'get':HOSTNAME}
        res = send_request(SERVER_URL, params)
        debug(res['response']['res'])
    else:
        usage()
        
        while True:
            params = {'set':HOSTNAME}
            res = send_request(SERVER_URL, params)
            time.sleep(2)
        
        
        
    
