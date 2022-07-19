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
import json
from subprocess import Popen, PIPE
from time import gmtime, strftime

from utils import *

this=os.path.basename(sys.argv[0])


# global variables
sigaling_artifact = ''
media_artifact = ''
sbc_release = ''

signaling_artifact_path = '/tmp/sbc_design/signaling'
media_artifact_path = '/tmp/sbc_design/media'

sig_artifact_path_after_unzip = signaling_artifact_path[:-4]
media_artifact_path_after_unzip = media_artifact_path + 'media01'

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
def signaling_artifact_process():
      if os.path.exists(media_artifact_path) == True:
        # Every new assessment task, we should remove old content
        run_cmd_with_std_output('/usr/bin/rm -rf ' + media_artifact_path)
      else:
        run_cmd_with_std_output('/usr/bin/mkdir -p  ' + media_artifact_path)
        
      run_cmd_with_std_error('/usr/bin/unzip -d ' + media_artifact_path + sigaling_artifact)

#################################################################################
def media_artifact_process():
      if os.path.exists(signaling_artifact_path) == True:
        # Every new assessment task, we should remove old content
        run_cmd_with_std_output('/usr/bin/rm -rf ' + signaling_artifact_path)
      else:
        run_cmd_with_std_output('/usr/bin/mkdir -p  ' + signaling_artifact_path)
        
      run_cmd_with_std_error('/usr/bin/unzip -d ' + signaling_artifact_path + media_artifact)

def load_signaling_artifacts():
        with open('sig_artifact_path_after_unzip' + '/bulk_adm/LCM_instantiate_params', 'r') as sigaling_file:
               signaling_data = json.load(sigaling_file)
        
#################################################################################
def main():
        parse_validate_opts()
        signaling_artifact_process()
        media_artifact_process()
        load_signaling_artifacts()
        load_media_artifacts()
        network_validation()
        domain_validation()
        interconnection_validation()
        sbc_feature_validation()
        timezone_ntp_validation()
        openstack_cloud_validation()
  
if __name__ == '__main__':
        main()

