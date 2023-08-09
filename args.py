import os
import subprocess
import requests
import sys
from colorama import Fore, Style, Back
import time
import functools
import yaml

#&                                                                                          GLOBALS
config = {
    "heading_type":1,
    "history_type":1,
    "diff_type":1,
    "commit_type":1,
    "final_type":1,

    "history_length":10,
    "diff_length":3,
    "final_length":1,
}
loaded_global_config = {}
local_config_file = '.gitwell'
global_config_file = '.gitwell_globals'



#&                                                                                           HELPERS
def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))

def pad(str, length, char=" "):
    if len(char) != 1:
        raise ValueError("Padding character must be a single character.")

    if length > len(str):
        return str + char * (length - len(str))
    else:
        return str[:length]
    
#&                                                                                                  
def load_config():
    # Config file names

    # Load the global config if it exists
    if os.path.exists(global_config_file):
        with open(global_config_file, 'r') as file:
            global_config = yaml.safe_load(file)
            config.update(global_config)
            loaded_global_config.update(global_config)
    else: 
        print(">> No global config, creating with defaults...")
        with open(global_config_file, 'w') as file:
            yaml.safe_dump(config, file)
            loaded_global_config.update(config)

        

    # Load the local config (this will override the global config)
    if os.path.exists(local_config_file):
        with open(local_config_file, 'r') as file:
            local_config = yaml.safe_load(file)
            config.update(local_config)
    else: 
        print(">> No local config, using globals")

#&                                                                                                  
def parse_args():
    for arg in sys.argv[1:]:
        min = 1
        max = 10
        key, value = [False, False]
        try:
            key, value = arg.split('=')
        except Exception as e:
            print('No config items found for:', arg)
            return

        if not key or not value:
            print('bad key or value:', key, value)
            return
        
        if key in config:
            print('config key:', key, value)

        elif 'global_' in key:
            globalKey = key.replace('global_', '')
            if globalKey in config:
                print('setting global val:', globalKey, value)
                if 'length' in key:
                    min = 1
                    max = 10
                if 'type' in key:
                    max = 4
                    min = 0

                loaded_global_config[globalKey] = clamp(int(value), min, max)

                with open(global_config_file, 'w') as file:
                    yaml.safe_dump(loaded_global_config, file)
                    load_config()
                    return
            else:
                print('global key not found:', globalKey)
        
        if 'length' in key:
            min = 1
            max = 10
        if 'type' in key:
            max = 4
            min = 0

        parsedValue = clamp(int(value), min, max)
        print(f"Setting key '{key}':{parsedValue}")
        config[key] = parsedValue

        with open(local_config_file, 'w') as file:
            yaml.safe_dump(config, file)
            load_config()




#&                                                                                                  
def main():
    try:
        clear_console()

        # Load the config and parse the command line arguments
        load_config()
        parse_args()

        # Print the final configuration
        # print(config)

        for key, value in config.items():
            print(f">> {pad(key, 15)} {value}")

    except Exception as e:
        print("Error creating commit:" + e)
"""
If this were a function that could generate and manage config

- take initial object as the first arg
- takes options:
    - useGlobals: boolean


useConfig(
    key="my_py_app",
    useGlobals=True
)
"""


# Execute main function
if __name__ == "__main__":
    main()
