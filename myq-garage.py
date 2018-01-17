#!/usr/bin/python3

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

from __future__ import print_function

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
TOKENTTL = config.get('main', 'TOKENTTL')

# ISY Configuration
USE_ISY = config.get('ISYConfiguration', 'USE_ISY') == 'True'
ISY_HOST = config.get('ISYConfiguration', 'ISY_HOST')
ISY_PORT = config.get('ISYConfiguration', 'ISY_PORT')
ISY_USERNAME = config.get('ISYConfiguration', 'ISY_USERNAME')
ISY_PASSWORD = config.get('ISYConfiguration', 'ISY_PASSWORD')
ISY_VAR_PREFIX = config.get('ISYConfiguration', 'ISY_VAR_PREFIX')

#MyQ API Configuration
if (BRAND.lower() == 'chamberlain'):
    SERVICE = config.get('APIglobal', 'ChamberSERVICE')
    APPID = config.get('APIglobal', 'ChamberAPPID')
    CULTURE = 'en'
    BRANDID = '2'
elif (BRAND.lower() == 'craftsman'):
    SERVICE = config.get('APIglobal', 'CraftSERVICE')
    APPID = config.get('APIglobal', 'CraftAPPID')
    CULTURE = 'en'
    BRANDID = '3'
else:
    print(BRAND, " is not a valid brand name. Check your configuration")

def setup_log(name):
   # Log Location
   PATH = os.getcwd()
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
        
class Device:
    def __init__(self, id, name, state, uptime):
        self.id = id
        self.name = name
        self.state = state
        self.time = uptime

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
    if int(r.status_code) == 404:
        print(str(id), " not found on ISY. Response was 404")
        LOGGER.error("%s not found on ISY. Response was 404", id)
    elif int(r.status_code) != 200:
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
        baseurl = SERVICE + "/api/v4"
        self.session = requests.Session()
        self.appid = APPID
        self.username = USERNAME
        self.password = PASSWORD
        self.headers = { "User-Agent": "Chamberlain/3.73",
                         "BrandId": BRANDID,
                         "ApiVersion": "4.1",
                         "Culture": CULTURE,
                         "MyQApplicationId": self.appid }
        self.authurl = baseurl+"/User/Validate"
        self.enumurl = baseurl+"/userdevicedetails/get"
        self.seturl  = baseurl+"/DeviceAttribute/PutDeviceAttribute"
        self.geturl  = baseurl+"/deviceattribute/getdeviceattribute"
        self.tokenfname="/tmp/myqtoken.json"
        self.tokentimeout=TOKENTTL
        self.read_token()

    def save_token(self):
        if (float(self.tokentimeout) > 0):
            ts=time.time()
            token_file={}
            token_file["SecurityToken"]=self.securitytoken
            token_file["TimeStamp"]=datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            json_data=json.dumps(token_file)
            f = open(self.tokenfname,"w")
            f.write(json_data)
            f.close()
            os.chmod(self.tokenfname, 0o600)

    def read_token(self):
        if (os.path.isfile(self.tokenfname)):
            with open(self.tokenfname,"r") as f:
                data = f.read()
            res = json.loads(data) if hasattr(json, "loads") else json.read(data)
            self.securitytoken = res["SecurityToken"]
        else:
            self.login()

    def login(self):
        payload = { "username": self.username, "password": self.password }
        req = self.session.post(self.authurl, headers=self.headers, json=payload)

        if (req.status_code != requests.codes.ok):
            print ("Login err code: " + req.status_code)
            sys.exit(-1)
        
        res = req.json()
        if (res["ReturnCode"] == "0"):    
            self.securitytoken = res["SecurityToken"]
            self.save_token()
        else: 
            print ("Authentication Failed")
            sys.exit(-1)

    # State = 0 for closed/off or 1 for open/on
    def set_state(self, device, device_type, desired_state):
        if device.state in ['Open', 'On'] and desired_state == 1:
            print(device.name + ' already ' + device.state + '.')
            sys.exit(5)
        if device.state in ['Closed', 'Off'] and desired_state == 0:
             print(device.name + ' already ' + device.state + '.')
             sys.exit(6)
        post_data = {
            "AttributeName"  : "desired" + device_type + "state",
            "MyQDeviceId"    : device.id,
            "ApplicationId"  : self.appid,
            "AttributeValue" : desired_state,
            "SecurityToken"  : self.securitytoken,
            "format"         : "json",
            "nojsoncallback" : "1"
        }

        self.session.headers.update({ "SecurityToken": self.securitytoken })
        payload = { "appId": self.appid, "SecurityToken": self.securitytoken }

        req = self.session.put(self.seturl, headers=self.headers, params=payload, data=post_data)

        if (req.status_code != requests.codes.ok):
            print ("Enum err code: " + req.status_code)
            return -1

        res = req.json()
        
        if (res["ReturnCode"] == "0"):
            print ("status changed")
            return True
        else:    
            print ("Can't set state, bad token?")
            return False
        
    def fetch_device_json(self):
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
            print ("Enum err code: " + req.status_code)
            return -1
        return req.json()

    def get_state(self, dev_type, value):
        # States value from API returns an interger, the index corresponds to the below list. Zero is not used. 
        GARAGE_STATES = ['','Open','Closed','Stopped','Opening','Closing']
        # "3" corresponds to a MyQ light
        if dev_type == 3:
            if value == 0:
                return "Off"
            elif value == 1:
                return "On"
        return GARAGE_STATES[value]
        
    def get_devices(self):
        res = self.fetch_device_json()
        # MyQ will tell us if our token is no longer valid. If so, delete the token and login again.
        if (res["ReturnCode"] == "-3333"):
            os.remove(self.tokenfname)
            self.read_token()
            res = self.fetch_device_json()
        instances = []
        if (res["ReturnCode"] == "0"):
            devices = [d for d in res["Devices"] if d["MyQDeviceTypeId"] in [2,3,17]]
            for d in devices:
                dev_type = int(d["MyQDeviceTypeId"])
                dev_id = d["MyQDeviceId"]
                for attr in d["Attributes"]:
                    if (attr["AttributeDisplayName"] == "desc"): 
                        desc = str(attr["Value"])
                    elif (attr["AttributeDisplayName"] in ["doorstate", "lightstate"]):
                        state = self.get_state(dev_type, int(attr["Value"]))
                        updtime = float(attr["UpdatedTime"])
                        timestamp = time.strftime("%a %d %b %Y %H:%M:%S", time.localtime(updtime / 1000.0))
                instances.append(Device(dev_id, desc, state, timestamp))
        return instances

def show_usage():
    print('Usage: \n' +
        '  ' + sys.argv[0] + ' status\n' +
        '  ' + sys.argv[0] + ' [open/close/on/off] [device ID]')
    sys.exit(1)

def myq_main():

    if len(sys.argv) < 2:
        show_usage()
    elif len(sys.argv) == 2:
        if sys.argv[1].lower() == 'status':
            desired_state = 2
        else:
            show_usage()
    else:
        if sys.argv[1].lower() == 'close' and sys.argv[2]:
            device_type = 'door'
            desired_state = 0
        elif sys.argv[1].lower() == 'open' and sys.argv[2]:
            device_type = 'door'
            desired_state = 1
        elif sys.argv[1].lower() == 'off' and sys.argv[2]:
            device_type = 'light'
            desired_state = 0
        elif sys.argv[1].lower() == 'on' and sys.argv[2]:
            device_type = 'light'
            desired_state = 1
        else:
            show_usage()
            
    myq = MyQ()
    device_instances = myq.get_devices()
    if desired_state == 2:
        for inst in device_instances:
            print ('{} is {}. Last changed at {}'.format(inst.name, inst.state, inst.time))
            LOGGER.info('%s is %s. Last changed at %s', inst.name, inst.state, inst.time)
            if USE_ISY:
                id, varname, init, value = isy_get_var_id(inst.name)
                value = 1 if inst.state in ["Open","On"] else 0
                isy_set_var_state(id, inst.name, varname, value)
    else:
        success = False
        for inst in device_instances:
            name = " ".join(sys.argv[2:])
            if name.lower() == inst.name.lower():
                myq.set_state(inst, device_type, desired_state)
                if USE_ISY:
                    id, varname, init, value = isy_get_var_id(inst.name)
                    isy_set_var_state(id, inst.name, varname, desired_state)
                print(inst.name + ' found. Setting state to ' + sys.argv[1].lower())
                success = True
        if not success:
            print(name + ' not found in available devices.')


#####################################################
if __name__ == "__main__":
    LOGGER = setup_log('myq-garage')
    LOGGER.info('==================================STARTED==================================')
    # Replace stdout with logging to file at INFO level
    # sys.stdout = SensorLogger(LOGGER, logging.INFO)
    # Replace stderr with logging to file at ERROR level
    sys.stderr = MyQLogger(LOGGER, logging.ERROR)
    myq_main()

