#!/usr/bin/env python2.7

## Python to interface with MyQ garage doors.
## Thanks to xKing for the new API stuff. Find him on the UDI Forums.

'''
The MIT License (MIT)

Copyright (c) 2015 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import requests
from requests.auth import HTTPBasicAuth
from requests.utils import quote
import sys
import time
import datetime
import os
import logging
import logging.handlers
import json

try:
    from ConfigParser import RawConfigParser
except ImportError as e:
    from configparser import RawConfigParser

# Try to use the C implementation first, falling back to python, these libraries are usually built-in libs. 
try:
    from xml.etree import cElementTree as ElementTree
except ImportError as e:
    from xml.etree import ElementTree
requests.packages.urllib3.disable_warnings()

config = RawConfigParser()
config.read('config.ini')

#main Configuration
USERNAME = config.get('main', 'USERNAME')
PASSWORD = config.get('main', 'PASSWORD')
BRAND = config.get('main', 'BRAND')

# ISY Configuration
USE_ISY = config.get('ISYConfiguration', 'USE_ISY')
ISY_HOST = config.get('ISYConfiguration', 'ISY_HOST')
ISY_PORT = config.get('ISYConfiguration', 'ISY_PORT')
ISY_USERNAME = config.get('ISYConfiguration', 'ISY_USERNAME')
ISY_PASSWORD = config.get('ISYConfiguration', 'ISY_PASSWORD')
ISY_VAR_PREFIX = config.get('ISYConfiguration', 'ISY_VAR_PREFIX')

#MyQ API Configuration
if (BRAND == 'Chamberlain' or BRAND == 'chamberlain'):
    SERVICE = config.get('APIglobal', 'ChamberSERVICE')
    APPID = config.get('APIglobal', 'ChamberAPPID')
    CULTURE = 'en'
elif (BRAND == 'Craftsman' or BRAND == 'craftsman'):
    SERVICE = config.get('APIglobal', 'CraftSERVICE')
    APPID = config.get('APIglobal', 'CraftAPPID')
    CULTURE = 'en'
else:
    print(BRAND, " is not a valid brand name. Check your configuration")


# States value from API returns an interger, the index corresponds to the below list. Zero is not used. 
STATES = ['',
        'Open',
        'Closed',
        'Stopped',
        'Opening',
        'Closing',
        ]
        
def setup_log(name):
   # Log Location
   PATH = os.path.dirname(sys.argv[0])
   if not os.path.exists(PATH + '/logs'):
       os.makedirs(PATH + '/logs')
   LOG_FILENAME = PATH + "/logs/myq-garage.log"
   LOG_LEVEL = logging.INFO  # Could be e.g. "DEBUG" or "WARNING"

   #### Logging Section ################################################################################
   LOGGER = logging.getLogger('sensors')
   LOGGER.setLevel(LOG_LEVEL)
   # Set the log level to LOG_LEVEL
   # Make a handler that writes to a file, 
   # making a new file at midnight and keeping 3 backups
   HANDLER = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=30)
   # Format each log message like this
   FORMATTER = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
   # Attach the formatter to the handler
   HANDLER.setFormatter(FORMATTER)
   # Attach the handler to the logger
   LOGGER.addHandler(HANDLER)
   return LOGGER

class MyQLogger(object):
    """ Logger Class """
    def __init__(self, logger, level):
        """Needs a logger and a logger level."""
        self.logger = logger
        self.level = level

    def write(self, logmessage):
        """ Only log if there is a message (not just a new line) """
        if logmessage.rstrip() != "":
            self.logger.log(self.level, logmessage.rstrip())

    def read(self, logmessage):
        """" Does nothing, pylist complained """
        pass
        
class DOOR:
    instances = []
    
    def __init__(self, id, name, state, uptime):
        DOOR.instances.append(self)
        self.id = id
        self.name = name
        self.state = state
        self.time = uptime
    
    def get_id(self):
        return self.id

        
def isy_set_var_state(id, name, varname, value):
    init, val = isy_get_var_state(id)
    if value == int(val):
        #print(varname, "is already set to ", val)
        LOGGER.info('%s is already set to %s', varname, val)
        return
    try:
        r = requests.get('http://' + ISY_HOST + ':' + ISY_PORT + '/rest/vars/set/2/' + id + '/' + str(value), auth=HTTPBasicAuth(ISY_USERNAME, ISY_PASSWORD))
    except requests.exceptions.RequestException as err:
        LOGGER.error('Caught Exception in isy_set_var_state: ' + str(err))
        return
    if int(r.status_code) != 200:
        if int(r.status_code) == 404:
            print(str(id), " not found on ISY. Response was 404")
            LOGGER.error("%s not found on ISY. Response was 404", id)
        else:
            print("Status change failed, response from ISY: ", str(r.status_code), str(r.text))
            LOGGER.error('Status change failed, response from ISY: %s - %s', str(r.status_code), str(r.text))
    else:
        print('{} changed successfully to {}'.format(varname, value))
  
def isy_get_var_state(id):
    try:
        r = requests.get('http://' + ISY_HOST + ':' + ISY_PORT + '/rest/vars/get/2/' + id, auth=HTTPBasicAuth(ISY_USERNAME, ISY_PASSWORD))
    except requests.exceptions.RequestException as err:
        LOGGER.error('Caught Exception in isy_get_var_state: ' + str(err))
        return        
    tree = ElementTree.fromstring(r.text)
    init = tree.find('init').text
    value = tree.find('val').text
    LOGGER.info('Get_Var_State: init: %s - val: %s', init, value)
    return init, value

def isy_get_var_id(name):
    varname = str(ISY_VAR_PREFIX + name.replace(" ", "_"))
    try:
        r = requests.get('http://' + ISY_HOST + ':' + ISY_PORT + '/rest/vars/definitions/2', auth=HTTPBasicAuth(ISY_USERNAME, ISY_PASSWORD))
    except requests.exceptions.RequestException as err:
        LOGGER.error('Caught Exception in isy_get_var_id: ' + str(err))
        return  
    #LOGGER.info('Get_Var_ID: Request response: %s %s', r.status_code, r.text)
    tree = ElementTree.fromstring(r.text)
    LOGGER.info('Searching ISY Definitions for %s', varname)
    valid = False
    for e in tree.findall('e'):
        if e.get('name') == varname:
                valid = True
                id, name = e.get('id'), e.get('name')
    if valid:
        #id, name = child.get('id'), child.get('name')
        LOGGER.info('State variable: %s found with ID: %s', name, id)        
    else:
        print("State variable: " + varname + " not found in ISY variable list")
        print("Fix your state variables on the ISY. Then enable the ISY section again.")
        sys.exit(5)
    init, value = isy_get_var_state(id)
    LOGGER.info('ISY Get Var ID Return - id: %s - varname: %s - init: %s - value: %s', id, varname, init, value)
    return id, varname, init, value

class MyQ:
    def __init__(self):
        self.session = requests.Session()
        self.appid = APPID
        self.baseurl = SERVICE
        self.username = USERNAME
        self.password = PASSWORD
        self.headers = { "User-Agent": "Chamberlain/2786", "MyQApplicationId": self.appid }
        self.authurl = self.baseurl+"/api/user/validatewithculture"
        self.enumurl = self.baseurl+"/api/v4/userdevicedetails/get"
        self.seturl  = self.baseurl+"/api/v4/DeviceAttribute/PutDeviceAttribute"
        self.geturl  = self.baseurl+"/api/v4/deviceattribute/getdeviceattribute"
        self.tokenfname="/tmp/myqdata.json"
        self.tokentimeout=60
        self.login()


    def login(self):
        payload = { "appId": self.appid, "username": self.username, "password": self.password, "culture": "en" }
        req=self.session.get(self.authurl, headers=self.headers, params=payload)

        if (req.status_code != requests.codes.ok):
            print "Login err code: " + req.status_code
            sys.exit(-1)
        
        res = req.json()
        
        if (res["ReturnCode"] == "0"):    
            self.securitytoken = res["SecurityToken"]
        else: 
            print "Authentication Failed"
            sys.exit(-1)
    

    # Door Action = 0 for closed or 1 for open
    def set_state(self, door, desired_state):
        if door.state == 'Open' and desired_state == 1:
            print(door.name + ' already open.')
            sys.exit(5)
        if door.state == 'Closed' and desired_state == 0:
             print(door.name + ' already closed.')
             sys.exit(6)
        post_data = {}
        post_data["AttributeName"]  = "desireddoorstate"
        post_data["MyQDeviceId"]       = door.id
        post_data["ApplicationId"]  = self.appid
        post_data["AttributeValue"] = desired_state
        post_data["SecurityToken"]  = self.securitytoken
        post_data["format"]  = "json"
        post_data["nojsoncallback"]  = "1"

        self.session.headers.update({ "SecurityToken": self.securitytoken })
        payload = { "appId": self.appid, "SecurityToken": self.securitytoken }

        req = self.session.put(self.seturl, headers=self.headers, params=payload, data=post_data)

        if (req.status_code != requests.codes.ok):
            print "Enum err code: " + req.status_code
            return -1

        res = req.json()
        
        if (res["ReturnCode"] == "0"):
            print "status changed"
            return True
        else:    
            print "Can't set state, bad token?"
            return False
              
    def get_doors(self):
        payload = { 
                "appId": self.appid, 
                "SecurityToken": self.securitytoken, 
                "filterOn": "true", 
                "format": 
                "json", 
                "nojsoncallback": "1" }
        self.session.headers.update({ "SecurityToken": self.securitytoken })

        req = self.session.get(self.enumurl, headers=self.headers, params=payload)

        if (req.status_code != requests.codes.ok):
            print "Enum err code: " + req.status_code
            return -1

        res = req.json()
        if (res["ReturnCode"] == "0"):
            for d in res["Devices"]:
                if (d["MyQDeviceTypeId"] == 2):
                    devid = d["MyQDeviceId"]
                    desc = None
                    state = None
                    updtime = None
                    for attr in d["Attributes"]:
                        if (attr["AttributeDisplayName"] == "desc"): 
                            desc = str(attr["Value"])
                        if (attr["AttributeDisplayName"] == "doorstate"): 
                            state = int(attr["Value"])
                            updtime = float(attr["UpdatedTime"])
                            timestamp = time.strftime("%a %d %b %Y %H:%M:%S", time.localtime(updtime / 1000.0))
                    DOOR(devid, desc, STATES[state], timestamp)
        return DOOR.instances


def gdoor_main():
    if len(sys.argv) < 2:
        print('Usage: ' + sys.argv[0] + ' [open/close/status] [door ID]')
        sys.exit(1)

    elif len(sys.argv) == 2:
        if sys.argv[1].lower() == 'status':
            desired_state = 2
        else:
            print('Usage: ' + sys.argv[0] + ' [open/close/status] [door ID]')
            sys.exit(1)
    else:
        if sys.argv[1].lower() == 'close' and sys.argv[2]:
            desired_state = 0
        elif sys.argv[1].lower() == 'open' and sys.argv[2]:
            desired_state = 1
        else:
            print('Usage: ' + sys.argv[0] + ' [open/close/status] [door ID]')
            sys.exit(1)
            
    myq = MyQ()
    door_instances = myq.get_doors()
    if desired_state == 2:
        for inst in door_instances:
            print ('{} is {}. Last changed at {}'.format(inst.name, inst.state, inst.time))
            LOGGER.info('%s is %s. Last changed at %s', inst.name, inst.state, inst.time)
            if USE_ISY:
                id, varname, init, value = isy_get_var_id(inst.name)
                if inst.state == "Open": value = 1
                else: value = 0
                isy_set_var_state(id, inst.name, varname, value)
    else:
        success = False
        for inst in door_instances:
            doorname = " ".join(sys.argv[2:])
            if doorname.lower() == inst.name.lower():
                myq.set_state(inst, desired_state)
                if USE_ISY:
                    id, varname, init, value = isy_get_var_id(inst.name)
                    isy_set_var_state(id, inst.name, varname, desired_state)
                print(inst.name + ' found. Setting state to ' + sys.argv[1].lower())
                success = True
        if not success:
            print(doorname + ' not found in available doors.')


#####################################################
if __name__ == "__main__":
    LOGGER = setup_log('myq-garage')
    LOGGER.info('==================================STARTED==================================')
    # Replace stdout with logging to file at INFO level
    # sys.stdout = SensorLogger(LOGGER, logging.INFO)
    # Replace stderr with logging to file at ERROR level
    sys.stderr = MyQLogger(LOGGER, logging.ERROR)
    gdoor_main()


