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
import sys

# Put your login information here
USERNAME = 'user@email.com'
PASSWORD = 'password'

# Do not change
SERVICE = 'https://myqexternal.myqdevice.com'


# Do not change the APPID this is global for the MyQ API
APPID = 'Vj8pQggXLhLy0WHahglCD4N1nAkkXQtGYpq2HrHD7H1nvmbT55KqtN6RSF4ILB%2fi'
CULTURE = 'en'

STATES = ['',
        'Open',
        'Closed',
        'Stopped',
        'Opening',
        'Closing',
        ]
## This is set for two garage doors. I should have made a class but I was learning. Add '' entries if you need more for now.
DOORNAME = ['','']
DOORSTATE = ['','',]
DOORLIST = ['','',]

# Door Action = 0 for closed or 1 for open
def set_doorstate(token, id, desired_state):
    currentstate = DOORSTATE[DOORLIST.index(id)]
    if DOORSTATE[DOORLIST.index(id)] == 'Open' and desired_state == 1:
         print('Door already open.')
         sys.exit(5)
    if DOORSTATE[DOORLIST.index(id)] == 'Closed' and desired_state == 0:
         print('Door already closed.')
         sys.exit(6)
    post_url = SERVICE + '/api/deviceattribute/putdeviceattribute'
    payload = {
        'ApplicationId': APPID,
        'AttributeName': 'desireddoorstate', 
        'DeviceId': id, 
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
    #token = (data['SecurityToken'])
    return data['SecurityToken']

def get_doors(token):
    global DOORNAME
    global DOORSTATE
    global DEVICELIST
    system_detail = SERVICE + '/api/UserDeviceDetails?appId=' + APPID + '&securityToken=' + token
    r = requests.get(system_detail)
    data = r.json()
    if data['ReturnCode'] != '0':
        print (data['ErrorMessage'])
        sys.exit(2)
    i = 0
    for device in data['Devices']:
        #MyQDeviceTypeId Doors == 2, Gateway == 1, Structure == 10, Thermostat == 11
        if device['MyQDeviceTypeId'] == 2:
            DOORNAME[i] = get_doorname(token, device['DeviceId'])
            DOORLIST[i] = device['DeviceId']
            DOORSTATE[i] = get_doorstate(token, device['DeviceId'])
            i += 1
            #print ('ID: ' + device['DeviceId'] + ' Type: ' + device['TypeName'] + ' is ' + state)
        #else:
            #print(device)
            #print ('ID: ' + device['DeviceId'] + ' Type: ' + str(device['TypeId']))

def get_doorstate(token, id):
    command = 'doorstate'
    doorstate_url = SERVICE + '/Device/getDeviceAttribute?appId=' + APPID + '&securityToken=' + token + '&devId=' + id + '&name=' + command
    r = requests.get(doorstate_url)
    data = r.json()
    if data['ReturnCode'] != '0':
        print (data['ErrorMessage'])
        sys.exit(3)
    return STATES[int(data['AttributeValue'])]

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
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print('Usage: ' + sys.argv[0] + ' [open/close/status] [open/close door ID number in config]')
        sys.exit(1)

    elif len(sys.argv) == 2:
        if sys.argv[1] == 'status':
            desired_state = 2
        else:
            print('Usage: ' + sys.argv[0] + ' [open/close/status] [open/close door ID number in config]')
            sys.exit(1)
    else:
        if sys.argv[1].lower() == 'close' and sys.argv[2]:
            desired_state = 0
        elif sys.argv[1].lower() == 'open' and sys.argv[2]:
            desired_state = 1
        else:
            print('Usage: ' + sys.argv[0] + ' [open/close/status] [open/close door ID number in config]')
            sys.exit(1)
    
    token = get_token()
    get_doors(token)
    if desired_state == 2:
        for i in DOORLIST:
            print (DOORNAME[DOORLIST.index(i)] + ' is ' + DOORSTATE[DOORLIST.index(i)] )
    else:
        if int(sys.argv[2]) > len(DOORLIST):
            print('Invalid Door number: ' + sys.argv[2])
            sys.exit(1)
        else:
            set_doorstate(token, DOORLIST[int(sys.argv[2])], desired_state)


#####################################################
if __name__ == "__main__":
    gdoor_main()
