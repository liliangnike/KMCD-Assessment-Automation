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


# global variables
sigaling_artifact = ''
media_artifact = ''
sbc_release = ''


#################################################################################
def parse_validate_opts():
        usage= '%prog options.'

        global sigaling_artifact, media_artifact, sbc_release
        description= 'The script is used for SBC L3 Design exam assignment assessment automatically.'
        parser = optparse.OptionParser(usage=usage, description=description)

        # Note: defaults action="store", type="string", dest="OPTION"
        parser.add_option("-s", "--sig_artifact", help="SBC signaling artifacts zip file")
        parser.add_option("-m", "--media_artifact", help="SBC media artifacts zip file")
        parser.add_option("-r", "--sbc_release", help="SBC release")

        # validate options
        try:
                (options, args) = parser.parse_args()

        except Exception, exc:
                err_log('Invalid options passed')
                log(traceback.format_exc())
                sys.exit(1)
                
        sigaling_artifact = options.sig_artifact
        media_artifact = options.media_artifact
        sbc_release = options.sbc_release

#################################################################################
def signaling_actifact_process():
        

#################################################################################
def main():
        parse_validate_opts()
        signaling_actifact_process()
        media_artifacts_process()
        network_validation()
        domain_validation()
        interconnection_validation()
        sbc_feature_validation()
        timezone_ntp_validation()
        openstack_cloud_validation()
  
if __name__ == '__main__':
        main()

