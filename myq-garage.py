#!/usr/bin/env python

## Python to interface with MyQ garage doors.

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
# Try to use the C implementation first, falling back to python, these libraries are usually built-in libs. 
try:
    from xml.etree import cElementTree as ElementTree
except ImportError, e:
    from xml.etree import ElementTree
requests.packages.urllib3.disable_warnings()

# Put your login information here
USERNAME = 'user@id.com'
PASSWORD = 'password'

# ISY Configuration
# Set USE_ISY = False if you don't wish to use the ISY features
USE_ISY = True
ISY_HOST = 'isy ip address'
ISY_PORT = '80'
ISY_USERNAME = 'admin'
ISY_PASSWORD = 'password'
ISY_VAR_PREFIX = 'MyQ_'

# Do not change this is the URL for the MyQ API
SERVICE = 'https://myqexternal.myqdevice.com'


# Do not change the APPID or CULTURE this is global for the MyQ API
APPID = 'Vj8pQggXLhLy0WHahglCD4N1nAkkXQtGYpq2HrHD7H1nvmbT55KqtN6RSF4ILB%2fi'
CULTURE = 'en'

# States value from API returns an interger, the index corresponds to the below list. Zero is not used. 
STATES = ['',
        'Open',
        'Closed',
        'Stopped',
        'Opening',
        'Closing',
        ]
        
class DOOR:
    instances = []
    
    def __init__(self, id, name, state, time):
        DOOR.instances.append(self)
        self.id = id
        self.name = name
        self.state = state
        self.time = time
    
    def get_id(self):
        return self.id

        
def isy_set_var_state(id, name, varname, value):
    init, val = isy_get_var_state(id)
    if value == int(val):
        print varname, "is already set to", val
        return
    r = requests.get('http://' + ISY_HOST + ':' + ISY_PORT + '/rest/vars/set/2/' + id + '/' + str(value), auth=HTTPBasicAuth(ISY_USERNAME, ISY_PASSWORD))
    if int(r.status_code) != 200:
        if int(r.status_code) == 404:
            print id, "not found on ISY. Response was 404"
        else:    
            print "Status change failed, response from ISY: ", r.status_code, r.text
    else:
        print varname, "changed successfully to", value
  
def isy_get_var_state(id):
    r = requests.get('http://' + ISY_HOST + ':' + ISY_PORT + '/rest/vars/get/2/' + id, auth=HTTPBasicAuth(ISY_USERNAME, ISY_PASSWORD))
    tree = ElementTree.fromstring(r.text)
    init = tree.find('init').text
    value = tree.find('val').text
    return init, value

def isy_get_var_id(name):
    varname = str(ISY_VAR_PREFIX + name.replace(" ", "_"))
    r = requests.get('http://' + ISY_HOST + ':' + ISY_PORT + '/rest/vars/definitions/2', auth=HTTPBasicAuth(ISY_USERNAME, ISY_PASSWORD))
    tree = ElementTree.fromstring(r.text)
    child = tree.find('e[@name="' + varname + '"]')
    if child:
        id, name = child.get('id'), child.get('name')
        #print id, name
    else:
        print("State variable: " + varname + " not found in ISY variable list")
        print("Fix your state variables on the ISY. Then enable the ISY section again.")
        sys.exit(5)
    init, value = isy_get_var_state(id)
    return id, varname, init, value
  
# Door Action = 0 for closed or 1 for open
def set_doorstate(token, name, desired_state):
    for inst in DOOR.instances:
        if inst.name == name:
            if inst.state == 'Open' and desired_state == 1:
                print(inst.name + ' already open.')
                sys.exit(5)
            if inst.state == 'Closed' and desired_state == 0:
                 print(inst.name + ' already closed.')
                 sys.exit(6)
            post_url = SERVICE + '/api/deviceattribute/putdeviceattribute'
            payload = {
                'ApplicationId': APPID,
                'AttributeName': 'desireddoorstate', 
                'DeviceId': inst.id, 
                'AttributeValue': desired_state, 
                'SecurityToken': token
                }
            r = requests.put(post_url, data=payload)
            data = r.json()
            if data['ReturnCode'] != '0':
                print (data['ErrorMessage'])
                sys.exit(1)
    


def get_token():
    login_url = SERVICE + '/Membership/ValidateUserWithCulture?appId=' + APPID + '&securityToken=null&username=' + USERNAME + '&password=' + PASSWORD + '&culture=' + CULTURE
    r = requests.get(login_url)
    data = r.json()
    if data['ReturnCode'] != '0':
        print (data['ErrorMessage'])
        sys.exit(1)
    return data['SecurityToken']

def get_doors(token):
    system_detail = SERVICE + '/api/UserDeviceDetails?appId=' + APPID + '&securityToken=' + token
    r = requests.get(system_detail)
    data = r.json()
    if data['ReturnCode'] != '0':
        print (data['ErrorMessage'])
        sys.exit(2)
    for device in data['Devices']:
        #MyQDeviceTypeId Doors == 2, Gateway == 1, Structure == 10, Thermostat == 11
        if device['MyQDeviceTypeId'] == 2:
            id = device['DeviceId']
            name = get_doorname(token, id)
            state, time = get_doorstate(token, id)
            DOOR(id, name,state,time)
    return DOOR.instances

def get_doorstate(token, id):
    command = 'doorstate'
    doorstate_url = SERVICE + '/Device/getDeviceAttribute?appId=' + APPID + '&securityToken=' + token + '&devId=' + id + '&name=' + command
    r = requests.get(doorstate_url)
    data = r.json()
    timestamp = float(data['UpdatedTime'])
    timestamp = time.strftime("%a %d %b %Y %H:%M:%S", time.localtime(timestamp / 1000.0))
    if data['ReturnCode'] != '0':
        print (data['ErrorMessage'])
        sys.exit(3)
    return STATES[int(data['AttributeValue'])], timestamp

def get_doorname(token, id):
    command = 'desc'
    doorstate_url = SERVICE + '/Device/getDeviceAttribute?appId=' + APPID + '&securityToken=' + token + '&devId=' + id + '&name=' + command
    r = requests.get(doorstate_url)
    data = r.json()
    if data['ReturnCode'] != '0':
        print (data['ErrorMessage'])
        sys.exit(3)
    return data['AttributeValue']


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
            print ('Usage: ' + sys.argv[0] + ' [open/close/status] [door ID]')
            sys.exit(1)
    
    token = get_token()
    get_doors(token)
    if desired_state == 2:
        for inst in DOOR.instances:
            print (inst.name +' is ' + inst.state +  '. Last changed at ' + inst.time)
            if USE_ISY:
                id, varname, init, value = isy_get_var_id(inst.name)
                if inst.state == "Open": value = 1
                else: value = 0
                isy_set_var_state(id, inst.name, varname, value)
    
    else:
        success = False
        for inst in DOOR.instances:
            doorname = " ".join(sys.argv[2:])
            if doorname.lower() == inst.name.lower():
                set_doorstate(token, inst.name, desired_state)
                if USE_ISY:
                    id, varname, init, value = isy_get_var_id(inst.name)
                    isy_set_var_state(id, inst.name, varname, desired_state)
                print(inst.name + ' found. Setting state to ' + sys.argv[1].lower())
                success = True
        if not success:
            print(doorname + ' not found in available doors.')


#####################################################
if __name__ == "__main__":
    gdoor_main()

