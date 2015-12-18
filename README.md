# myq-garage
Python Chamberlain Garage Door interface

Python used to interface with my MyQ garage doors. 
Load it as a module, or download it and run directly.

1. Download myq-garage.py to your device. Or use git ("git clone https://github.com/Einstein42/myq-garage.git")
2. Put it in the same folder as your relay server if using any of io_guy's products.
3. chmod 755 myq-garage.py
4. Edit the file and put your myq username and password. Including ISY information if applicable.

Then use like so:
Command Line options:  ./myq-garage.py [open/close/status] [door name]
Door name is the name you set in the MyQ webpage for the device. If you don't know your door name, 
then just ./myq-garage.py status and it will return the doornames and status from the MyQ portal. 

Requires the requests package in python
1. apt-get install python-requests
OR
2. apt-get install python-pip
3. pip install requests

DONT FORGET TO CREATE YOUR STATE VARIABLES IN THE ISY, it will tell you if you forgot.
There isn't currently a way to create these via API, I will update as soon as ISY allows state variable creation.

Variable format is the setting from myq-garage.py "ISY_VAR_PREFIX + your door name. Substitute any spaces with '_' as 
ISY doesn't allow spaces in variable names.
eg. 'Big Door' is my door name in MyQ and my variable prefix is MyQ_ so I create the variable MyQ_Big_Door

Variable is set to 1 when open, 0 when closed.

If you want to run this so it updates your state variables in ISY automatically every 5 minutes
you can add a crontab entry on your linux/raspbian like so:

1. crontab -e
2. new line at the botton
3. */5 * * * * /path/to/myq-garage.py status

I wouldn't recommend doing more than every 5 minutes as the Chamberlain MyQ API is 'unofficial' therefore if we 
take down their servers from flooding them with requests, I doubt the'd be happy.

Cheers - E
