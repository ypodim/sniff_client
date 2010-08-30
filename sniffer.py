#!/usr/bin/python
# -*- coding: utf-8 -*-

import time, httplib2, urllib, simplejson, thread, sys, socket, os, signal
from datetime import datetime, timedelta
from Queue import Queue
from subprocess import *


__version__ = 0.5


import logging, os, platform
import logging.handlers

LOG_FILENAME = os.path.join(os.path.dirname(__file__), "output.log")
my_logger = logging.getLogger('MyLogger')
my_logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=1000000, backupCount=5)
my_logger.addHandler(handler)

def debug(arg):
    my_logger.debug('%s' % arg)
    print '%s' % arg




#----------------- Start of options -----------

# server where that receives the reportss
port   = 80
host   = 'bluescan.media.mit.edu'
server = 'http://%s' % host
urlpath= '/post_report'

# socket connection timeout
timeout = 120

# number of seconds in the past that we maintain BT scans for
# while server is unreachable
cutoff  = 3600
              
# sleep-time in between consecutive reports in seconds
sleeptime = 10

# date-time mask used to represent timestamps
# eg. 2009-01-21 18:20:00
datetime_mask = "%Y-%m-%d %H:%M:%S" 

# name of the current scanning device 
# (try looking in file "hostname" first)

if platform.system() == 'Darwin':
    reporter_name = socket.gethostname()
else:
    try :
        reporter_name = open('/etc/hostname','r').read().strip()
    except: 
        debug('Hostname not found! Bailing.')
        sys.exit()

# location of the current scanning device 
# (try looking in file "locationde3cx" first)
try :   location = open('location','r').read().strip()
except: location = ''

# key to authenticate reporter
try :   key = open('key','r').read().strip()
except: key = 'no_key'

#----------------- End of options -----------


# queue that holds device info obtained from the BT module
queued = Queue()



def report_data(queue, now):
    debug('sending......')
    start_time = time.time()
    
    # Convert the python dictionary into a JSON string
    queued_str = simplejson.dumps(queue)
    
    # Create HTTP POST parameters and values and report them
    report = {'reports':queued_str, 'location':location, 'reporter':reporter_name, 'tstamp':now, 'key':key}
    
    body = urllib.urlencode(report)
    
    debug('check 1......sending about %s bytes' % len(body))
    try:
        
        h = httplib2.Http(timeout=timeout)
        debug('check 2......')
        resp, content = h.request('%s:%s%s'%(server,port,urlpath), method="POST", body=body)
        if resp['status'] == '200':
            debug('response:%s' % content)
            # Count the number of device entries that will be reported
            total = 0
            for devs in queue.values():
                total += len(devs)
            debug('%s reported %02d devices' % (datetime.now(), total))
            # Reset the queues
            queue = {}
        else:
            debug(content)
            debug('%s'%report)
            debug('what happened to the server? status: %s' % resp['status'])
            
    except Exception, e:
        debug('Connection problem: %s' % e)
        debug('%s items in queue' % len(queue))
        
    debug('concluded TX in %s\n' % (time.time()-start_time))
    return queue


def process_reports():
    alpha           = 0.5 # low pass filter to smooth out rssi report
    pending_reports = {}  # holds list of pending reports
    
    debug('Reporter started')
    while 1:
        start_time = time.time()
        
        debug('items in Q: %s' % queued.qsize())
        
        devices = {}
        while queued.qsize():
            item = queued.get()
 
            mac = item[0]
            if mac not in devices:
                devices[mac] = {}
                
            if len(item) == 3:
                mac, cls, rssi = item
                
                devices[mac]['class'] = cls
                
                if 'rssi' in devices[mac]:
                    devices[mac]['rssi'] = alpha * rssi + (1-alpha) * devices[mac]['rssi']
                else:
                    devices[mac]['rssi'] = rssi

            if len(item) == 2:
                mac, name = item
                devices[mac]['name'] = name
            
        now = datetime.now().strftime(datetime_mask)
        if devices:
            pending_reports[now] = devices
        
        # clear any old data
        to_delete = []
        for date in pending_reports:
            dtime = datetime.strptime(date, datetime_mask)
            if dtime < datetime.now() - timedelta(seconds=cutoff):
                to_delete.append(date)
        for td in to_delete:
            del pending_reports[td]
        
        # send reports, or keep them on failure
        pending_reports = report_data(pending_reports, now)
        
        debug('%d items in pending_reports' % len(pending_reports))
        
        processing_time = time.time() - start_time
        if processing_time < sleeptime:
            time.sleep(sleeptime - processing_time)
            
    debug('OUT OF THE LOOP')

        

def report_failure():
    port = 3457
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.sendto( '%s' % reporter_name, (host, port) )
    client.close()



def loop_bluez(p):
    if p:
        report_failure()
        sys.exit()
    
    com = ['hcidump', '-x', '-V']
    p = Popen(com, stdout=PIPE)
    
    debug( 'opened hcidump in spinq mode')
        
    thread.start_new_thread(process_reports, ())

    previous_addr = ''
    while 1:
        line = p.stdout.readline().strip().split()
        debug(line)
        if line and line[0] == 'bdaddr':
            addr = line[1]

            cls = 0
            if len(line) > 7:
                cls = int(line[7], 16)

            rssi = '-100'
            if len(line) > 9:
                rssi = int(line[9])
                previous_addr = addr
                #print 'found %s class %s rssi %s' % (addr, cls, rssi)
                #post_data(addr, cls, rssi)

            queued.put( (addr, cls, rssi) )
        if line and line[0] == 'Complete':
            name = ''.join([x for x in line[3:]])
            if name[:2] != '0x':
                debug( '%s is now know as %s' % (previous_addr, name) )
                #rem_dev_name_signal(previous_addr, name)
                queued.put( (addr, name) )


def loop_lightblue():
    try:
        import lightblue
    except:
        debug('LightBlue not found')
        sys.exit()
    
    thread.start_new_thread(process_reports, ())
    
    #nearby_devices = lightblue.finddevices()
    while 1:
        #import lightblue
        #nearby_devices = lightblue.finddevices()
        #for addr, name, cls in nearby_devices:
            #rssi = '-100'
            #queued.put( (addr, cls, rssi) )
            #queued.put( (addr, name) )
        
        #del lightblue
        print 'looping'
        time.sleep(5)
    


    
def handler(signum, frame):
    print '\n\n\n\nSignal handler called with signal', signum
    #sys.exit()


if __name__=='__main__':


    


    # Set the signal handler and a 5-second alarm
    for i in xrange(20):
        try:
            signal.signal(i, handler)
        except Exception, e:
            print 'sig: %s' % e
            
    #signal.signal(signal.SIGHUP, handler)
    #signal.signal(signal.SIGQUIT, handler)
    #signal.signal(signal.SIGTERM, handler)
    



    debug('Starting service v%s' % __version__)
    

    #while not succeeded:
    try:
        com = ['hcitool', 'spinq']
        p = Popen(com).wait()
        loop_bluez(p)
    except:
        debug('Bluez not found')
        loop_lightblue()







