# telekom_fon_connect

This little python script here will autoconnect you with your Telekom hotspot credetials @ a Telekom_FON Hotspot. **ONLY** Telekom customers @ **Telekom_FON** named Hotspot.

Works only if login page looks like this:
<img src="http://fs5.directupload.net/images/180813/d2clfvef.jpg"  alt="Telekom_FON Login Page"/></a>

I use it as deamon to check every 30s for online status direct at system boot with systemd. Host system is a Rapsberry Pi 1B with 2 wlan usb sticks and iptables for natting.
On top (as you should always do when using uncypted wlan networks) i use a openvpn connection which is started automatic at system startup via systemd.timer when statusfile exists.

## Getting Started

The script is testet/used on Raspbian/Debian Stretch (9) with python version 2.7.13 and 3.5.3.
The script is fully compatible to python2 and python3, doesn't matter :)  

On Debian you first need to install:  
python2:
```
apt-get install python-requests python-bs4 python-configparser
```
python3:
```
apt-get install python3-requests python3-bs4 python-configparser
```

1. ! On Raspberry Pi 1B the script takes a while to load the request library, please be patient
2. ! Im neither a developer nor an python expert. So this code can be not as you are normal used to.

### Installing

Clone this repository and use the systemd service file if you want to run it as daemon at system startup.

## Usage

A quick overview you can get by calling the script with -h.

```
pi@raspberry:~#/opt/telekom_fon_connect/telekom_fon_connect.py -h
usage: telekom_fon_connect.py [-h] [-c CONFIG] [-d] [-s] [-v] [-V]

This script check take care of your online status on a Telekom_FON Hotspot and
will login you if necessary

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Pass path of config file to script. If nothing given
                        script will try to read env var
                        telekom_fon_connect_cfg
  -d, --daemon          Run this script as a daemon checking any n time for
                        online status and connect if needed. If not option not
                        given the script will only connect and afterwards die
  -s, --statusfile      Safe your external ip in a statusfile defined in
                        configfile
  -v, --verbose         If log_level is debug, script will print this also to
                        stdout instead of save in file only
  -V, --version         show program's version number and exit
```

The always needed config file hold some other informations:
```
[telekom_fon_connect]
log_level: DEBUG
log_file: /tmp/debug.log
status_file: /tmp/online.txt
fon_username: ******@t-mobile.de
fon_password: xxx-xxx-xxx
test_url: http://online-status.cf
rlp_request_whitelist: ["HSPNAME", "LANGUAGE", "LOCATIONID", "LOCATIONNAME", "VNPNAME", "WISPURL", "WISPURLHOME"]
telekom_api_endpoint: https://rlp.telekom.de/wlan/rest/
session_api_url: contentapi
login_api_url: login
sleeptime: 30
```
Some explanations to config file:
```
fon_username: ******@t-mobile.de
```
Please replace the stars with your mobile number, for example 491512345678.
Using number only is equal to using username mentionend on the login page.
Adding @t-mobile.de to the number is equal to using e-mail mentionend on the login page.
You can find/obtain your crentials either in the "Connect App - HotSpot Manager" or by sending an [sms](https://www.telekom.de/hilfe/mobilfunk-mobiles-internet/mobiles-internet-e-mail/hotspot/konfiguration-nutzen-sicherheit/sms-befehle-zur-nutzung-von-hotspot-mit-mobilfunk-zugangsdaten)

```
test_url: http://online-status.cf
```
Domain of mine which delivers on http request a 301 to https. With a https request you get your ip as json response and as x-your-ip Header. Is used to define online status.
Using http here is important, unauthenticated hotspot users aren't allowed to do https (excluding some whitelisted) requests, they timeout.

```
rlp_request_whitelist
```
Currently needed informations for creating a session to login. Maybe more informations needed/wanted in future.

```
sleeptime
```
Seconds to wait in deamon mode between online checks.

### Credits

A big thanks going out to these persons, for their questions and answers which helped me with their code snippets:

python requests module: https://www.pythonforbeginners.com/requests/using-requests-in-python  
HTML parse with Beautiful Soap: https://www.crummy.com/software/BeautifulSoup/bs4/doc/  
Filter Formdata: https://stackoverflow.com/a/16480521  
String list to python list: https://stackoverflow.com/a/988251  
Usage of python argparse: https://pymotw.com/2/argparse/  
Debug logging of (http) requests in correct Debug channel: https://stackoverflow.com/a/34285632  

## Contributing ...

... is welcome. Either to correct my english, adding some nice new features, fix my python code or reporting errors.
If you report an error, please try to reproduce and copy the full error message.
Best case would be to tell the fully procedure and run in debug mode.
Feel free to open issues or merge requests.
Gerne auch in Deutsch ;)

## Further ideas to do
- Make useragent configurable to replace the current python-requests/VERSION
- Save logout url maybe in statusfile and add trigger to logout via script (SIGUSR ?)
- Use [sessions](http://docs.python-requests.org/en/master/user/advanced/#session-objects) in python request(s)
- Determine telekom_api_endpoint out of source code. Maybe via start.html ?

## License

This project is licensed under the WTFPL (Do What The Fuck You Want To Public License)- see the [LICENSE.md](LICENSE.md) file for details
