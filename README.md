# myq-garage
Python Chamberlain Garage Door interface

Python used to interface with my MyQ garage doors. 

Load it as a module, or download it and chmod 755 myq-garage.py

Edit the file and put your myq username and password. Including ISY information if applicable.

Then use like so:

Command Line options:  ./myq-garage.py [open/close/status] [door number]

Requires the requests package in pythong

If you don't have pip then install it. 'apt-get install python-pip'

Then install the requests package 'pip install requests'

DONT FORGET TO CREATE YOUR STATE VARIABLES IN THE ISY, it will tell you if you forgot.

Cheers - E
