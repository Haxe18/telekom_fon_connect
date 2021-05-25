#!/usr/bin/python
## Imports ##
import argparse                                                                          # To parse arguments
import logging                                                                           # Import logging module
try:                                                                                     # Import ConfigParser Module
    import ConfigParser                                                                  # Python 2
except ImportError:
    import configparser                                                                  # Python 3
import os                                                                                # Import os to read config file path from env var
import requests                                                                          # For http(s) requests in python
import sys                                                                               # For exit (codes) and for correct http debug Log in debug logging
import time                                                                              # For sleep in while loop
from bs4 import BeautifulSoup                                                            # Import BeautifulSoup for parsing html
import ast                                                                               # To convert the imported whitelist dict out of config to an python dict (is a string when read via config)
import json                                                                              # To communicate with telekom rest api
try:                                                                                     # Import of urllib needed for url decode
    from urllib.parse import unquote                                                     # Python 3
except ImportError:
    from urllib import unquote                                                           # Python 2

def initialize_logger(level,log_file,args):
    logger = logging.getLogger()                                                         # Start logger
    loglvl = getattr(logging, level)                                                     # Get int of defined level
    logger.setLevel(loglvl)                                                              # Set Log to int level
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")               # Define log format

    if level == 'DEBUG':                                                                 # If Debug level include httplib/http.client to debug requests in detail and log to File
        try:                                                                             # Used by request module, needed to set debug
            import http.client as http_client                                            # Python 3
        except ImportError:
             import httplib as http_client                                               # Python 2
        http_client.HTTPConnection.debuglevel = 1                                        # If log level debug, set lib for requests also to debug (see headers)

        # Enable Logs form request (which uses urllib3)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(level)
        requests_log.propagate = True

        # create file handler
        handler_file = logging.FileHandler(log_file,"w")
        handler_file.setFormatter(formatter)
        logger.addHandler(handler_file)

    # create console handler
    handler_console = logging.StreamHandler()
    handler_console.setFormatter(formatter)
    logger.addHandler(handler_console)
    if level == "DEBUG" and args.verbose == False:                                       # If log level debug and verbose mode not wanted
        handler_console.setLevel(logging.INFO)                                           # Set level to info for console handler - file takes debug

def reset_http_debug_out(http_log):
    # Remember to reset sys.stdout!
    sys.stdout = sys.__stdout__
    # Remove \r in Log, remove the byte prefix - is already a string with b and no byte tyoe in http_log.content list, replace \n to be printed as newline and remove lines with only ' in
    debug_info = ''.join(http_log.content).replace('\\r', '').replace('b\'', '\'').replace('\\n', '\n').replace('\'', '')

    # Remove empty lines and print in Debug Channel
    logging.debug("\n".join([ll.rstrip() for ll in debug_info.splitlines() if ll.strip()]))

#Return Stuff save response code also to check if success !
def do_request(url,level,do_head_only=False,get_session=False,want_header=False,post=False,note_timeout=True):
    # Define some things #
    return_stuff = {}                                                                    # Create empty return_stuff dict
    timeout = 30                                                                         # Default timeout for each request is 10 seconds

    if level == 'DEBUG':                                                                 # If Level is debug we get some info we want in debug channel
        # HTTP stream handler
        class WritableObject:
            def __init__(self):
                self.content = []
            def write(self, string):
                self.content.append(string)

        # A writable object
        http_log = WritableObject()
        # Redirection
        sys.stdout = http_log

    # Do all requests in a try to catch every error
    try:
        # if we want the location header only
        if do_head_only == True:
            r = requests.head(url=url, timeout=timeout)                                  # Do head request
            return_stuff['rsp_code'] = r.status_code                                     # Save response code of request
            if want_header != False:                                                     # If we want a specific header
                return_stuff['rsp_content'] = r.headers.get(want_header)                 # Return this header
            else:
                return_stuff['rsp_content'] = r.status_code                              # If no wanted header @ head request defined, return status code again
        else:
            if post != False:                                                            # Post data defined ...
                r = requests.post(url=url, data=post, timeout=timeout)                   # ... do post request
                return_stuff['rsp_code'] = r.status_code                                 # Save response code of request
                if get_session == True:                                                  # Want session header
                    return_stuff['rsp_content'] = r.cookies['JSESSIONID']                # Return Session header
                else:
                    return_stuff['rsp_content'] = r.text                                 # Save response of request (encode utf-8 for shure ;)
            else:
                r = requests.get(url=url, timeout=timeout)                               # Do normal get request
                return_stuff['rsp_code'] = r.status_code                                 # Save response code of request
                return_stuff['rsp_content'] = r.text                                     # Save response of request (encode utf-8 for shure ;)

        if level == 'DEBUG':                                                             # If Level is debug we get some info we want in debug Channel
            reset_http_debug_out(http_log)                                               # Call final part of HTTP Debug output

        return return_stuff                                                              # Return filled dict with needed stuff
    except requests.exceptions.Timeout as e:                                             # I got sometimes timeoutes @ final login
        if note_timeout == False:                                                        # If we got it @ Login ignore, i was always nevertheless online
            logging.debug( str(e) + " occured when requesting page, ignoring")           # Print debug message about the timeout
            return_stuff['rsp_code'] = 200                                               # Return 200 - because online and ignore error
            return_stuff['rsp_content'] = 200                                            # Return 200 - because online and ignore error
            return return_stuff                                                          # Return defined stuff
        else:
            logging.error('Timeout after ' + str(timeout) + ' seconds, request aborted, will exit from here now. Please try again later')
            return 'error'
    except requests.exceptions.RequestException as e:                                    # Catch all network errors
        logging.error("An error occurred when doing the request, will exit now. Please try again later")
        logging.debug(e)
        return 'error'

def do_login(username,password,test_url,rlp_request_whitelist,telekom_api_endpoint,session_api_url,login_api_url,loglvl,login_url=None):
    ## START Do a request to get the Login URL and save session ##
    if login_url is None:
        logging.info('Doing request to ' + test_url + ' to get hotspot status page')
        login_page = do_request(url=test_url, do_head_only=True, want_header='location', level=loglvl)

        if login_page is 'error':                                                         # If request failed and return is only offline
            return 'offline'                                                              # return direct offline, errors are already thrown

        login_url = login_page['rsp_content']                                             # Save url of login page

        if login_page['rsp_content'] is None or login_page['rsp_code'] != 302:            # Redirect is done (correctly) via 302, if not something went wrong
            logging.error('Error when getting hotspot status page, something went wrong. Will exit from here now')
            logging.debug('Location-Header of request to ' + test_url + ' was ' +  login_url + 'HTTP-Status was ' + str(login_page['rsp_code']))
            return 'offline'
    else:
        logging.debug('Login Url is already defined, use it')

    logging.debug('Hotspot login and status page is ' + login_url)
    ## END Do a request to get the Login URL ##

    ## START Do request to login page to get source code and get post informations to post ##
    logging.info('Doing request to hotspot login page to fetch source code')
    logging.debug('Doing request to ' + login_url + ' to fetch source code to create post data')
    fon_source = do_request(url=login_url, level=loglvl)                                  # Get source of login page to extract some infos to create a session

    if fon_source is 'error':                                                             # If request failed and return is only offline
        return 'offline'                                                                  # Return direct offline, errors are already thrown

    logging.debug('Start parsing html to get post data')
    try:                                                                                  # Try parsing ...
        parsed_fon_html = BeautifulSoup(fon_source['rsp_content'], 'lxml')                # Parse HTML of login page request
        #logoff_page = 'logoffpage'                                                       # Save logoff url
        form = parsed_fon_html.body.find('div', attrs={'id':'page-container'})            # Find div with post infos
        logout_url = form.find('div').get('data-ng-init').split("'")[1]                   # Get Logout url: in div page-container -> angular div with name/class/id (whatever called in angular) data-ng-init -> split at ' and save url in the 's
        inputs = form.find_all('input') # Parse out all inputs                            # Get inputs of div
        divdata = dict( (field.get('name'), field.get('value')) for field in inputs)      # Fill formdata dict
        logging.debug('Post data found')
    except Exception as e:                                                                # ... catch exception if html code could not be parsed as wanted
        logging.error('Error when parsing html code to get post data. Either a (temporary) error or script is not working anymore. Will try again')
        logging.debug('Got error ' + str(e) + ' when parsing html to get form data')
        return 'offline'

    # Filter dict, keep only elements in post_data_whitelist
    rlp_request = {}                                                                      # Define new dict with post data
    for key in rlp_request_whitelist:                                                     # For each whitelist key
        rlp_request[key] = divdata[key]                                                   # Fill new dict key with key value of old

    # We got the urls dirct of of source code, there it is encoded but for json post later we need it plain/decoded
    divdata['WISPURL'] = unquote(divdata['WISPURL'])                                      # Decode Url for correct json post
    divdata['WISPURLHOME'] = unquote(divdata['WISPURLHOME'])                              # Decode Url for correct json post

    postdata = json.dumps( {'location': {}, 'partnerRegRequest': {}, 'rlpRequest': divdata, 'session': {}, 'user': {}} )    # Create json to post to api

    logging.debug('Postdata created')
    ## END Do request to Login page to get source code and get post informations to post ##

    ## START Starting login session at Telekom rest api ##
    url = telekom_api_endpoint + session_api_url                                          # Build url to get session
    login_check = do_request(url, get_session = True, post=postdata, level=loglvl)      # Do post request to get session

    if login_check is 'error':                                                            # If request failed and return is only offline
        return 'offline'                                                                  # return direct offline, errors are already thrown

    if login_check['rsp_code'] != 200:                                                    # Check if session generated. 200 all okay. HTTP-400 when wrong informations posted. 302 if post empty 
        logging.error('Failed to begin login session @ telekom api. Please try again later')
        return 'offline'                                                                  # Creation of session failed, we must try in next run - offline

    session = login_check['rsp_content']                                                  # Save session

    logging.info('Session @ Telekom api successfull created')
    ## END Starting login session at Telekom rest api ##

    ## START Try to login with credentials @ Telekom fon hotspot ##
    url = telekom_api_endpoint + login_api_url + ';jsessionid=' + session                 # Build url with session for login check
    logindata = json.dumps( {"username": username,"password": password} )                 # Create json with login credentials
    login_status = do_request(url, post=logindata, level=loglvl)                          # Do login

    if login_status is 'error':                                                           # If request failed and return is only offline
        return 'offline'                                                                  # return direct offline, errors are already thrown

    dec_json = json.loads(login_status['rsp_content'])                                    # Decode json return of api

    if 'errors' in dec_json and 'redirect' not in dec_json:                               # Catch errors
        logging.error('Error when login with ' + username + ' @ Telekom fon hotspot, got message ' + dec_json['errors'][0]['description'] )  # Print received error message
        logging.error('Maybe your given credentials are not valid, please check')
        return 'offline'

    logging.info('Authentification @ Telekom api was successfull, got login url')
    login_url = dec_json['redirect']['url']                                               # Login url @ local router is given from telekom api after auth. Save to do login
    ## END Try to login with credentials @ Telekom fon hotspot ##

    ## START Login ##
    online_status = do_request(url=login_url, note_timeout=False, level=loglvl)           # Do the final request to be online, ignore timeouts here

    if online_status is 'error':                                                          # If request failed and return is only offline
        return 'offline'                                                                  # return direct offline, errors are already thrown

    if online_status['rsp_code'] == 200:                                                  # 200 if timeout or login okay
        logging.info('Login successfull, you are online :)')
        logging.info('To logout, please open ' + logout_url)
        return 'online'
    else:
        logging.info('Login failed, you are (maybe) not online')                          # Something went wrong ...
        return 'offline'
    ## END LOGIN

def do_statusfile(statusfile, action='remove', test_url=None, loglvl = None):
    if action is 'create' and test_url is not None and loglvl is not None:
        your_ip = do_request(url=test_url.replace("http", "https"), do_head_only=True, want_header='X-your-ip', level=loglvl) #Do head to https test_url to fetch ip header
        if your_ip is not 'error':                                                        # If request for ip was success, return is not only offline
            f = open(statusfile, "w")                                                     # Open status file to write
            f.write(your_ip['rsp_content'])                                               # Write current ip saved in content to file
            logging.debug('Written your current ip ' + your_ip['rsp_content'] + ' successfull to file ' + statusfile)
        else:
            logging.debug('Error when terminating your ip for statusfile ' + statusfile + ', will not write statusfile')
    else:
        if os.path.isfile(statusfile):                                                    # If statusfile exists
            os.remove(statusfile)                                                         # Remove, we are offline
            logging.debug('Statusfile successfull deleted')

def main():
    ## START argument parser ##
    parser = argparse.ArgumentParser(description='This script check take care of your online status on a Telekom_FON Hotspot and will login you if necessary')  # Define help description
    parser.add_argument('-c', '--config',
                    help='Pass path of config file to script. If nothing given script will try to read env var telekom_fon_connect_cfg')
    parser.add_argument('-d', '--daemon', action='store_true',
                    help='Run this script as a daemon checking any n time for online status and connect if needed. If not option not given the script will only connect and afterwards die')
    parser.add_argument('-s', '--statusfile', action='store_true',
                    help='Safe your external ip in a statusfile defined in configfile')
    parser.add_argument('-v', '--verbose', action='store_true',
                    help='If log_level is debug, script will print this also to stdout instead of save in file only')
    parser.add_argument('-V', '--version', action='version', version='%(prog)s 1.0')
    args = parser.parse_args()
    ## END argument parser ##

    ## START lookup for arg or env var to load config ##
    if args.config != None:                                                               # Check if config argument is defined
        cfg_file = args.config
    else:
        if 'telekom_fon_connect_cfg' not in os.environ:                                   # If the env var with config path is not defined
            logging.error('Env var telekom_fon_connect_cfg not found - please set or pass path as argument');
            sys.exit(1)
        cfg_file = os.environ['telekom_fon_connect_cfg']                                  # Safe config path out of env var
    try:                                                                                  # Try to include configparser
        Config = ConfigParser.ConfigParser()                                              # Python2
    except NameError:
        Config = configparser.ConfigParser()                                              # Python3

    try:                                                                                  # Try to read config
        Config.read(cfg_file)                                                             # Open configfile and read
    except Exception as e:                                                                # Catch exception if wrong file given
        logging.error('Error when loading config file, please check path and syntax')
        logging.debug('Got error ' + str(e) + ' when loading config file')
        sys.exit(1)
    ## END lookup for arg or env var to load config ##

    ## START Save infos out of config file in vars ##
    loglvl = Config.get('telekom_fon_connect', 'log_level')
    log_file = Config.get('telekom_fon_connect', 'log_file')
    username = Config.get('telekom_fon_connect', 'fon_username')
    password = Config.get('telekom_fon_connect', 'fon_password')
    test_url = Config.get('telekom_fon_connect', 'test_url')
    rlp_request_whitelist = ast.literal_eval(Config.get('telekom_fon_connect', 'rlp_request_whitelist'))  # Convert list string to list via a safe eval python way
    telekom_api_endpoint = Config.get('telekom_fon_connect', 'telekom_api_endpoint')
    session_api_url = Config.get('telekom_fon_connect', 'session_api_url')
    login_api_url = Config.get('telekom_fon_connect', 'login_api_url')
    sleeptime = Config.get('telekom_fon_connect', 'sleeptime')
    if args.statusfile is True:                                                           # If status file wanted
        statusfile = Config.get('telekom_fon_connect', 'status_file')                     # Save status file var for config
    ## END Save infos out of config file in vars ##

    # Start logging
    initialize_logger(loglvl,log_file,args)                                               # Pass log level and log file path as arguments to logger setup

    # Print some infos @ startup
    logging.debug('Working with configfile: ' + cfg_file)
    logging.info('log_level is : ' + loglvl)

    ## START While Loop for online check ##
    run = True                                                                            # while forever

    while run == True:                                                                    # While run = True, run forever
        online_request = do_request(url=test_url, do_head_only=True, want_header='location',level=loglvl)  # Do head request to check online status

        if online_request is 'error':                                                     # If request failed and return is only offline
            status = 'offline'                                                            # Return direct offline, errors are already thrown
            if args.statusfile is True:                                                   # If status file wanted
                do_statusfile(statusfile=statusfile, action='remove')                     # Remove statusfile, we are offline
        elif online_request['rsp_code'] == 301 and online_request['rsp_content'] == test_url.replace("http", "https") + '/':   # We are online because we got 301 redirect to https (with correct location)
            logging.debug('You are online')
            status = 'online'                                                             # Set success to online
            if args.statusfile is True:                                                   # If statusfile wanted
                do_statusfile(statusfile=statusfile, action='create', test_url=test_url, loglvl=loglvl) # Create statusfile
        else:                                                                             # We are not online, try login
            login_url = online_request['rsp_content']                                     # Save location from head online test to do login
            logging.info('You are not online, try to login now')
            if args.statusfile is True:                                                   # If status file wanted
                do_statusfile(statusfile=statusfile, action='remove')                     # Remove statusfile, we are offline
            status = do_login(username,password,test_url,rlp_request_whitelist,telekom_api_endpoint,session_api_url,login_api_url,loglvl,login_url)
            if status is 'online' and args.statusfile is True:                            # If request was success, return is not only offline and statusfile wanted
                do_statusfile(statusfile=statusfile, action='create', test_url=test_url, loglvl=loglvl) # Create statusfile

        if args.daemon is False and status is 'online':                                   # No deamon mode wanted, exit the while loop after first run
            logging.info('Your are now ' + status + ' and because no deamon mode selected i will exit now bye')
            run = False
        if args.daemon is True:                                                           # If daemon mode, sleep
            logging.debug('You are ' + status + ' sleeping now for ' + str(sleeptime) + ' before checking status again')
            time.sleep(float(sleeptime))                                                  # Sleep for n seconds before check status again
    ## END While Loop for online check ##

if __name__ == '__main__':
        sys.exit(main())                                                                  # If no arg, pass none
