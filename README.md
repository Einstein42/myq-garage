# myq-garage
Python Chamberlain Garage Door interface

Python used to interface with my MyQ garage doors. 

Load it as a module, or download it and chmod 755 myq-garage.py

Edit the file and put your myq username and password. Including ISY information if applicable.

Then use like so:

Command Line options:  ./myq-garage.py [open/close/status] [door name]

Door name is the name you set in the MyQ webpage for the device.

Requires the requests package in python

If you don't have pip then install it. 'apt-get install python-pip'

Then install the requests package 'pip install requests'

DONT FORGET TO CREATE YOUR STATE VARIABLES IN THE ISY, it will tell you if you forgot.

Variable format is ISY_VAR_PREFIX + MyQ Door name. Substitute any spaces with '_' as 
ISY doesn't allow spaces in variable names.
eg. 'Big Door' is my door name in MyQ and my variable prefix is MyQ_ so I create the variable MyQ_Big_Door

Variable is set to 1 when open, 0 when closed.

Cheers - E
