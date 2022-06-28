#!/usr/bin/env python

import os
import sys
import getopt
import re
import pdb
import socket
import commands
import traceback
import platform
import shutil
import signal
import optparse
import exceptions
import subprocess
from subprocess import Popen, PIPE


from time import gmtime, strftime

this=os.path.basename(sys.argv[0])

#################################################################################
def parse_validate_opts():
        # Module to parse the option value and then validate it #
        usage= '%prog options.'

        global action, check_en, config_file
        description= 'This script is used for growing a pair of LCP hosts, supports both bulk configuration and interactive configuration.'
        parser = optparse.OptionParser(usage=usage, description=description)

        # Note: defaults action="store", type="string", dest="OPTION"
        parser.add_option("-a", "--action", dest='action', default='interactive', help="action interactive|bulk|gen_template|flex_bulk|gen_flex_bulk_template")
        parser.add_option("-c", "--check", action='store_true', dest='check_en', default=False, help="enable check option")
        parser.add_option("-f", "--file", action='store', dest='filename', help="file of bulk configuration")

        # validate options
        try:
                (options, args) = parser.parse_args()

                if (options.action != 'interactive') and (options.action != 'bulk') and (options.action != 'gen_template') \
                        and (options.action != 'flex_bulk') and (options.action != 'gen_flex_bulk_template') :
                        log('Action: ' + options.action + ' is not valid.')
                        parser.print_help()
                        sys.exit(1)

        except Exception, exc:
                err_log('Invalid options passed')
                log(traceback.format_exc())
                sys.exit(1)
        action = options.action
        check_en = options.check_en
        config_file = options.filename
        


#################################################################################
def main():
        parse_validate_opts()
  
if __name__ == '__main__':
        main()

