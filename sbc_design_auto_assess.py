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
#import yaml

import xml.etree.ElementTree as ET   # to parse XML file, such as signaling netconf XML

from subprocess import Popen, PIPE
from time import gmtime, strftime

from utils import *

this=os.path.basename(sys.argv[0])


# linux commands alias
UNZIP = '/usr/bin/unzip '

# Return value
PASS = 0
FAIL = 1

# global variables
signaling_artifact = ''
media_artifact = ''
sbc_release = ''

signaling_artifact_path = '/tmp/sbc_design/signaling'
media_artifact_path = '/tmp/sbc_design/media'

sig_artifact_path_after_unzip = ''
media_artifact_path_after_unzip = media_artifact_path + '/media01'

media_mgw_vnf_package_path = media_artifact_path + '/Nokia_media_MGW_VNF_Package'

netconf_xml_namespace = '{http://nokia.com/yang/IMS/LCP}'

# global file full path name
signaling_instantiation_json = ''
signaling_netconf_xml = ''
media_instantiation_json = ''
media_mgw_yaml = ''

# global dict to save loaded data
signaling_instantiation_json_data = {}
signaling_netconf_xml_data = {}
media_instantiation_json_data = {}
media_mgw_yaml_data = {}

# global list used to do assess
signaling_subnet_list = []
media_pim_subnet_list = []

# global keys of instantiation json dict
external_virtual_links = 'extVirtualLinks'
grantless_mode = 'grantlessMode'
software_image = 'softwareImages'
vim_connection_info = 'vimConnectionInfo'
external_managed_virtual_links = 'extManagedVirtualLinks'
flavor_id = 'flavourId'
api_version = 'apiVersion'
zone = 'zones'
instant_level_id = 'instantiationLevelId'
additional_params = 'additionalParams'
computer_resource_flavors = 'computeResourceFlavours'


#################################################################################
def parse_validate_opts():
        usage= '%prog options.'

        global signaling_artifact, media_artifact, sbc_release
        description= 'The script is used for SBC L3 Design exam assignment assessment automatically.'
        parser = optparse.OptionParser(usage=usage, description=description)

        # Note: defaults action="store", type="string", dest="OPTION"
        parser.add_option("-s", "--sig_artifact", type="string", help="SBC signaling artifacts zip file")
        parser.add_option("-m", "--media_artifact", type="string", help="SBC media artifacts zip file")
        parser.add_option("-r", "--sbc_release", type="string", help="SBC release")

        # validate options
        try:
                (options, args) = parser.parse_args()

        except Exception, exc:
                err_log('Invalid options passed')
                log(traceback.format_exc())
                sys.exit(1)
                
        signaling_artifact = options.sig_artifact
        media_artifact = options.media_artifact
        sbc_release = options.sbc_release

	if signaling_artifact == None:
		err_log("Please check the usage, -s or --sig_artifact is expected. Siganling artifact is missing.")
		sys.exit(1)

	if media_artifact == None:
		err_log("Please check the usage, -m or --media_artifact is expected. Media artifact is missing.")
        	sys.exit(1)

#################################################################################
def media_artifact_process():
	global media_instantiation_json, media_mgw_yaml

	if os.path.exists(media_artifact_path) == True:
		# Every new assessment task, we should remove old content
		run_cmd_with_std_output('/usr/bin/rm -rf ' + media_artifact_path)
       
	# 1. unzip media artifact zip file 
	run_cmd_with_std_error(UNZIP + media_artifact + ' -d ' +  media_artifact_path)

	# 2. unzip Nokia media MGW VNF package to parse Nokia_media_MGW.yaml
	run_cmd_with_std_error(UNZIP + media_artifact_path + '/Nokia_media_MGW_VNF_Package.zip -d ' + media_mgw_vnf_package_path)

	media_instantiation_json = media_artifact_path_after_unzip + '/Nokia_media_MGW.instantiate.json'
	media_mgw_yaml = media_mgw_vnf_package_path + '/Nokia_media_MGW.yaml'

#################################################################################
def signaling_artifact_process():
	global sig_artifact_path_after_unzip, signaling_instantiation_json, signaling_netconf_xml

	if os.path.exists(signaling_artifact_path) == True:
		# Every new assessment task, we should remove old content
		run_cmd_with_std_output('/usr/bin/rm -rf ' + signaling_artifact_path)
       
	# unzip signaling artifact zip file 
	run_cmd_with_std_error(UNZIP + signaling_artifact + ' -d ' + signaling_artifact_path)

	sig_artifact_path_after_unzip = (signaling_artifact_path + '/' + signaling_artifact)[:-4]
	signaling_instantiation_json = sig_artifact_path_after_unzip + '/bulk_adm/LCM_instantiate_params.json'
	signaling_netconf_xml = sig_artifact_path_after_unzip + '/bulk_netconf/netconfprov_artifact.xml'


def load_signaling_artifacts():
	global signaling_instantiation_json_data, signaling_netconf_xml_data
	# Parse signaling instantiation json file
        with open(signaling_instantiation_json, 'r') as sigaling_file:
        	signaling_instantiation_json_data = json.load(sigaling_file)

	# Parse XML
	tree = ET.parse(signaling_netconf_xml)
	signaling_netconf_xml_data = tree.getroot()
       
def load_media_artifacts():
	global media_instantiation_json_data, media_mgw_yaml_data 
	
	# Parse media instantiation json file
	media_instantiation_json
	with open(media_instantiation_json, 'r') as media_file:
		media_instantiation_json_data = json.load(media_file)

def check_signaling_subnet():
	global signaling_subnet_list

	for elem in signaling_netconf_xml_data.findall(netconf_xml_namespace + 'IPv4SubnetInformation'):
		subnet_name = elem.find(netconf_xml_namespace + 'SubnetName').text
		signaling_subnet_list.append(subnet_name)
	
		# 1. MTU size check
		if elem.find(netconf_xml_namespace + 'mtu_size').text != '1500':
			err_log('MTU size of {0} is not 1500'.format(subnet_name) )
			sys.exit(FAIL)

	# 2. Name check
	if len(signaling_subnet_list) < 5:
		err_log('Subnet numbers of signaling plane should be no less than 5.')
		sys.exit(FAIL)

	pattern = re.compile('.*oam.*|.*gm.*|.*mw.*|.*rx.*|.*rf.*', re.IGNORECASE)
	for net in signaling_subnet_list:
		if pattern.match(net) == None:
			err_log('The subnet {0} is not in the name list as required in SBC L3 design assignment doc'.format(net) )		


def check_media_subnet():
	global media_pim_subnet_list

	# for differ SBC release, instantiation json file might be differenent
	
	for links in media_instantiation_json_data[external_virtual_links]:
		#if re.match('', links['id']):
		if sbc_release == 'R20.0':
			print (links['id'])

#################################################################################
def main():
        parse_validate_opts()
        signaling_artifact_process()
        media_artifact_process()
        load_signaling_artifacts()
        load_media_artifacts()
	check_signaling_subnet()
	check_media_subnet()
        #domain_validation()
        #interconnection_validation()
        #sbc_feature_validation()
        #timezone_ntp_validation()
        #openstack_cloud_validation()
  
if __name__ == '__main__':
        main()

