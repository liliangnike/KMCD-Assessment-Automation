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

import xml.etree.ElementTree as ET   # to parse XML file, such as signaling netconf XML

from subprocess import Popen, PIPE
from time import gmtime, strftime

from utils import *

this=os.path.basename(sys.argv[0])

# linux commands alias
UNZIP = '/usr/bin/unzip '
FIND = '/usr/bin/find '

# Return values
PASS = 0
FAIL = 1

# global variables
artifacts_errors_counter = 0

signaling_artifact = ''
media_artifact = ''
sbc_release = 'R22.5'
student_num = 0

signaling_artifact_path = '/tmp/sbc_design/signaling'
media_artifact_path = '/tmp/sbc_design/media'

sig_artifact_path_after_unzip = ''
media_artifact_path_after_unzip = media_artifact_path + '/media01'
media_bulk_zip = media_artifact_path_after_unzip + '/bulk.zip'
media_bulk_install0_scr = media_artifact_path_after_unzip + '/bulk/INSTALL0.SCR'

ims_lcp_namespace = '{http://nokia.com/yang/IMS/LCP}'
isbc_sig_namespace = '{http://nokia.com/yang/isbc-sig}'

# global file full path name
signaling_instantiation_json = ''
signaling_netconf_xml = ''
media_instantiation_json = ''

# global dict to save loaded data
signaling_instantiation_json_data = {}
signaling_netconf_xml_data = {}
media_instantiation_json_data = {}

# global data structure to save information from netconfprov XML
netconf_ipv4_subnet_list = None
netconf_pcscf_profile_table = None
netconf_ipv4_subnet_list = []
netconf_pcscf_profile_table = None
netconf_pcscf_profile_table_record = None
netconf_basic_information = None
netconf_cfed_port_table = None
netconf_cfed_port_table_record = None
netconf_pnaptr_table = None
netconf_pnaptr_table_record = None
netconf_sblp_table = None
netconf_sblp_table_record = None
netconf_stn_sr_table_record = None
netconf_global_parameters = None
netconf_cbam_information = None
netconf_cbam_info_vims = None
netconf_cloud_deploy_info = None
netconf_ngss_parameters = None
netconf_spare_records_table = None
netconf_spare_records_table_record = None
netconf_sdp_profile_table = None
netconf_sdp_profile_table_record = None

netconf_mi_ip_xml_obj_list = []
netconf_mi_ip_dict = {}

netconf_ims_ip_list = [] # IMS Floating IP numbers should be only 1, use list to count all service IPs

netconf_feph_ip_xml_obj_list = []
netconf_feph_ip_dict = {}

netconf_dfed_ip_xml_obj_list = []
netconf_dfed_ip_dict = {}

netconf_cnfg_ip_xml_obj_list = []
netconf_cnfg_ip_dict = {}

netconf_cfed_ip_xml_obj_list = [] 
netconf_cfed_ip_dict = {}

# global data structure to save information from media instantiation json 
media_flavor_list = []
media_openstack_info_list = []
media_ip_dict = {}

# global list used to do assess
signaling_subnet_list = []
media_network_list = []
media_pim_subnet_list = []
media_codec_list = []

#################################################################################
def parse_validate_opts():
	usage= '%prog options.'

	global signaling_artifact, media_artifact, sbc_release, student_num
	description= 'The script is used for SBC Design exam assignment assessment automatically.'
	parser = optparse.OptionParser(usage=usage, description=description)

	# Note: defaults action="store", type="string", dest="OPTION"
	parser.add_option("-s", "--sig_artifact", type="string", help="SBC signaling artifacts zip file")
	parser.add_option("-m", "--media_artifact", type="string", help="SBC media artifacts zip file")
	parser.add_option("-r", "--sbc_release", type="string", help="SBC release")
	parser.add_option("-n", "--student_num", type="int", help="Student index number 1-9")

	# validate options
	try:
		(options, args) = parser.parse_args()

	except Exception, exc:
		err_log('Invalid options passed')
		log(traceback.format_exc())
		sys.exit(FAIL)
                
	signaling_artifact = options.sig_artifact
	media_artifact = options.media_artifact
	sbc_release = options.sbc_release
	student_num = options.student_num

	if signaling_artifact == None:
		err_log("Please check the usage, -s or --sig_artifact is expected. Signaling artifact is missing.")
		sys.exit(FAIL)

	if media_artifact == None:
		err_log("Please check the usage, -m or --media_artifact is expected. Media artifact is missing.")
		sys.exit(FAIL)

	if student_num == 0:
		err_log("Please check the usage, -n or --student_num is expected. Student number (1-9) is missing.")
		sys.exit(FAIL)

#################################################################################
def media_artifact_process():
	global media_instantiation_json, media_extension_json, media_mgw_yaml

	log('Media artifacts zip file is processing.')
	if os.path.exists(media_artifact_path) == True:
		cmdline = '/usr/bin/rm -rf ' + media_artifact_path
		try:
			(output, error) = run_cmd_with_std_error(cmdline)
		except Exception, exc:
			log(str(exc))
			sys.exit(FAIL)
	log('Old path for media artifact processing is removed.') 
       
	# 1. unzip media artifact zip file 
	cmd = UNZIP + media_artifact + ' -d ' +  media_artifact_path
	try:
		(output, error) = run_cmd_with_std_error(cmd)
	except Exception, exc:
		log(str(exc))
		sys.exit(FAIL)
	log('New media artifact zip file is unzipped successfully.')

	# 2. unzip bulk.zip
	cmd = UNZIP + media_bulk_zip + ' -d ' + media_artifact_path_after_unzip
	try:
		(output, error) = run_cmd_with_std_error(cmd)
	except Exception, exc:
		log(str(exc))
		sys.exit(FAIL)
	log('Media bulk zip file is unzipped successfully.')
	
	media_instantiation_json = media_artifact_path_after_unzip + '/Nokia_media_MGW.instantiate.json'
	media_extension_json = media_artifact_path_after_unzip + '/Nokia_media_MGW.extensions.json'
	log('Media artifacts processing is done.')

#################################################################################
def signaling_artifact_process():
	global sig_artifact_path_after_unzip, signaling_instantiation_json, signaling_netconf_xml

	log('Signaling artifacts zip file is processing.')
	if os.path.exists(signaling_artifact_path) == True:
		cmdline = '/usr/bin/rm -rf ' + signaling_artifact_path
		try:
			(output, error) = run_cmd_with_std_error(cmdline)
		except Exception, exc:
			log(str(exc))
			sys.exit(FAIL)
	log('Old path for signaling artifact processing is removed.') 

	cmd = UNZIP + signaling_artifact + ' -d ' + signaling_artifact_path
	try:
		(output, error) = run_cmd_with_std_error(cmd)
	except Exception, exc:
		log(str(exc))
		sys.exit(FAIL)
	log('New signaling artifact zip file is unziped successfully.')

	cmd = FIND + signaling_artifact_path + ' -name bulk_adm'
	try:
		(signaling_instantiation_json, error) = run_cmd_with_std_output(cmd)
	except Exception, exc:
		log(str(exc))
		sys.exit(FAIL)
	signaling_instantiation_json = signaling_instantiation_json.strip('\n') + '/LCM_instantiate_params.json'

	cmd = FIND + signaling_artifact_path + ' -name bulk_netconf'
	try:
		(signaling_netconf_xml, error) = run_cmd_with_std_output(cmd)
	except Exception, exc:
		log(str(exc))
		sys.exit(FAIL)
	signaling_netconf_xml = signaling_netconf_xml.split('\n')[1] + '/netconfprov_artifact.xml'
	log('Signaling artifacts processing is done.')

#################################################################################
def load_signaling_artifacts():
	global signaling_instantiation_json_data, signaling_netconf_xml_data

	# Parse signaling instantiation json file
	if not os.path.exists(signaling_instantiation_json):
		err_log('Signaling plane instantiation json file {0} does not exist'.format(signaling_instantiation_json))
		sys.exit(FAIL)
	with open(signaling_instantiation_json, 'r') as signaling_file:
        	signaling_instantiation_json_data = json.load(signaling_file)

	log('Signaling instantiation json file is loaded successfully.')

	# Parse XML
	tree = ET.parse(signaling_netconf_xml)
	signaling_netconf_xml_data = tree.getroot()
	log('Signaling netconf provisioning XML file is parsed successfully.')
	
#################################################################################
def extract_netconfprov_xml_info(signaling_netconf_xml_data):
	global netconf_basic_information
	global netconf_global_parameters
	global netconf_cbam_information, netconf_cbam_info_vims
	global netconf_cloud_deploy_info
	global netconf_ipv4_subnet_list
	global netconf_mi_ip_xml_obj_list, netconf_mi_ip_dict
	global netconf_ims_ip_list
	global netconf_feph_ip_xml_obj_list, netconf_feph_ip_dict
	global netconf_dfed_ip_xml_obj_list, netconf_dfed_ip_dict
	global netconf_cnfg_ip_xml_obj_list, netconf_cnfg_ip_dict
	global netconf_cfed_ip_xml_obj_list, netconf_cfed_ip_dict
	global netconf_pcscf_profile_table, netconf_pcscf_profile_table_record
	global netconf_cfed_port_table, netconf_cfed_port_table_record
	global netconf_pnaptr_table, netconf_pnaptr_table_record
	global netconf_sblp_table, netconf_sblp_table_record
	global netconf_stn_sr_table_record
	global netconf_ngss_parameters
 	global netconf_spare_records_table, netconf_spare_records_table_record
	global netconf_sdp_profile_table, netconf_sdp_profile_table_record

	log('Extracting information from netconfprov XML is starting...')
	netconf_basic_information = signaling_netconf_xml_data.find(ims_lcp_namespace + 'BasicInformation')
	log('Extracting BasicInformation is done.')

	netconf_global_parameters = signaling_netconf_xml_data.find(isbc_sig_namespace + 'GlobalParameters')
	log('Extracting GlobalParameters is done.')

	netconf_cbam_information = signaling_netconf_xml_data.find(ims_lcp_namespace + 'cbam_information')
	netconf_cbam_info_vims = netconf_cbam_information.find(ims_lcp_namespace + 'vims')
	log('Extracting cbam_information is done.')

	netconf_cloud_deploy_info = signaling_netconf_xml_data.find(ims_lcp_namespace + 'cloud_deployment_information')
	log('Extracting cloud_deployment_information is done.')

	netconf_ipv4_subnet_list = signaling_netconf_xml_data.findall(ims_lcp_namespace + 'IPv4SubnetInformation')
	log('Extracting IPv4SubnetInformation is done.')

	netconf_mi_ip_xml_obj_list = signaling_netconf_xml_data.findall(ims_lcp_namespace + 'IPv4ServiceIP-MI')
	extract_service_ips_to_dict(netconf_mi_ip_xml_obj_list, netconf_mi_ip_dict)
	log('Extracting IPv4ServiceIP-MI is done.')

	netconf_ims_ip_list.append(signaling_netconf_xml_data.find(ims_lcp_namespace + 'IPv4ServiceIP-IMS').find(ims_lcp_namespace + 'IPAddressList').find(ims_lcp_namespace + 'IPAddress').text)
	log('Extracting IPv4ServiceIP-IMS is done.')

	netconf_feph_ip_xml_obj_list = signaling_netconf_xml_data.findall(ims_lcp_namespace + 'IPv4ServiceIP-FEPH')
	extract_service_ips_to_dict(netconf_feph_ip_xml_obj_list, netconf_feph_ip_dict, True, True)
	log('Extracting IPv4ServiceIP-FEPH is done.')

	netconf_dfed_ip_xml_obj_list = signaling_netconf_xml_data.findall(ims_lcp_namespace + 'IPv4ServiceIP-DFED')
	extract_service_ips_to_dict(netconf_dfed_ip_xml_obj_list, netconf_dfed_ip_dict, True, True)
	log('Extracting IPv4ServiceIP-DFED is done.')

	netconf_cnfg_ip_xml_obj_list = signaling_netconf_xml_data.findall(ims_lcp_namespace + 'IPv4ServiceIP-CNFG')
 	extract_service_ips_to_dict(netconf_cnfg_ip_xml_obj_list, netconf_cnfg_ip_dict, True, True)
	log('Extracting IPv4ServiceIP-CNFG is done.')

	netconf_cfed_ip_xml_obj_list = signaling_netconf_xml_data.findall(ims_lcp_namespace + 'IPv4ServiceIP-CFED')
	extract_service_ips_to_dict(netconf_cfed_ip_xml_obj_list, netconf_cfed_ip_dict, True, True)
	log('Extracting IPv4ServiceIP-CFED is done.')

	netconf_pcscf_profile_table = signaling_netconf_xml_data.find(isbc_sig_namespace + 'PcscfProfileTable')
	netconf_pcscf_profile_table_record  = netconf_pcscf_profile_table.find(isbc_sig_namespace + 'Record')
	log('Extracting PcscfProfileTable is done.')

	netconf_cfed_port_table = signaling_netconf_xml_data.find(isbc_sig_namespace + 'CFEDPortTable')
	netconf_cfed_port_table_record = netconf_cfed_port_table.find(isbc_sig_namespace + 'Record')
	log('Extracting CFEDPortTable is done.')

	netconf_pnaptr_table = signaling_netconf_xml_data.find(isbc_sig_namespace + 'PNAPTRTargetURITable')
	netconf_pnaptr_table_record = netconf_pnaptr_table.find(isbc_sig_namespace + 'Record')
	log('Extracting PNAPTRTargetURITable is done.')

	netconf_sblp_table = signaling_netconf_xml_data.find(isbc_sig_namespace + 'SblpProfileTable')
	netconf_sblp_table_record = netconf_sblp_table.find(isbc_sig_namespace + 'Record')
	log('Extracting SblpProfileTable is done.')

	netconf_stn_sr_table_record = signaling_netconf_xml_data.find(isbc_sig_namespace + 'STNSRTable').find(isbc_sig_namespace + 'Record')
	log('Extracting STNSRTable is done.')

	netconf_ngss_parameters = signaling_netconf_xml_data.find(isbc_sig_namespace + 'NGSSParameters')
	log('Extracting NGSSParameters is done.')

	netconf_spare_records_table = signaling_netconf_xml_data.find(isbc_sig_namespace + 'SpareRecordsTable')
	netconf_spare_records_table_record = netconf_spare_records_table.find(isbc_sig_namespace + 'Record')
	log('Extracting SpareRecordsTable is done.')

	netconf_sdp_profile_table = signaling_netconf_xml_data.find(isbc_sig_namespace + 'SDPProfileTable')
	netconf_sdp_profile_table_record = netconf_sdp_profile_table.find(isbc_sig_namespace + 'Record')
	log('Extracting SDPProfileTable is done.')
	log('Extracting information from netconfprov XML is finished.')

################################################################################
def extract_service_ips_to_dict(service_ip_obj_list, service_ip_dict, to_get_2nd_ip = False, to_get_2nd_connectivity_ip = False):
	''' dict example: service_ip_dict{'default' : {'fixed' : ['10.10.10.96']}} '''
	second_ip_obj = None
	second_connectivity_ip_obj = None
	
	log('Extracting signaling service IP addresses is starting...')

	for service in service_ip_obj_list:
		ni_type = service.find(ims_lcp_namespace + 'NIType').text
		floating_or_fixed = service.find(ims_lcp_namespace + 'FloatingOrFixed').text
		ip_address_list = service.findall(ims_lcp_namespace + 'IPAddressList')
		
		log('Extracted NI type is {0}, IP type is {1}.'.format(ni_type, floating_or_fixed))

		if ni_type not in service_ip_dict.keys():
			service_ip_dict[ni_type] = { floating_or_fixed : [] }
		elif floating_or_fixed not in service_ip_dict[ni_type].keys():
			service_ip_dict[ni_type][floating_or_fixed] = []

		for ip_address in ip_address_list:
			ip = ip_address.find(ims_lcp_namespace + 'IPAddress').text
			log('Extracted IP address is {0}.'.format(ip))
			service_ip_dict[ni_type][floating_or_fixed].append(ip)
			if to_get_2nd_ip:
				second_ip_obj = ip_address.find(ims_lcp_namespace + 'SecondIPAddress')
				if second_ip_obj != None:
                			second_ip = second_ip_obj.text
					log('Extracted Second IP address is {0}.'.format(second_ip))
                			service_ip_dict[ni_type][floating_or_fixed].append(second_ip)

			if to_get_2nd_connectivity_ip:
				second_connectivity_ip_obj = ip_address.find(ims_lcp_namespace + 'SecondConnectivityIP')
				if second_connectivity_ip_obj != None:
					second_connectivity_ip = second_ip_obj.text
					log('Extracted Second Connectivity IP address is {0}.'.format(second_connectivity_ip))
                			service_ip_dict[ni_type][floating_or_fixed].append(second_connectivity_ip)

	log('Extracting signaling service IP addresses is done.')

#################################################################################
def load_media_artifacts():
	global media_instantiation_json_data, media_extension_json_data, media_mgw_yaml_data 
	global media_codec_list
	
	# Parse media instantiation json file
	if not os.path.exists(media_instantiation_json):
		err_log('Media plane instantiation json file {0} does not exist'.format(media_instantiation_json))
		sys.exit(FAIL)
	with open(media_instantiation_json, 'r') as instantiation_file:
		media_instantiation_json_data = json.load(instantiation_file)

	log('Media instantiation json file is loaded successfully.')

	# Read INSTALL0.SCR to get media codec list
	with open(media_bulk_install0_scr, 'r' ) as fd:
		for line in fd:
			if line.startswith('#') == True or line.__len__() == 0 or line.isspace() == True :
				continue
			else:
				if re.match('define profile capacity media codec gw.media.capacity.mpu.*', line):
					if line.strip().split(' ')[7] != '0':
						media_codec_list.append(line.strip().split(' ')[6])

	log('Media codec list is loaded successfully.')

#################################################################################
def extract_media_instantiation_info(media_instantiation_json_data):
	global media_flavor_list
	global media_openstack_info_list
	global media_ip_dict

	log('Extracting information from media instantiation file is starting...')
	for resource in media_instantiation_json_data['computeResourceFlavours']:
		if resource['vimFlavourId'] not in media_flavor_list:
			media_flavor_list.append(resource['vimFlavourId'])
	log('Extracting media vm flavor information is done.')

	for link in media_instantiation_json_data['extVirtualLinks']:
		if link['id'] == 'pim_voice1_ecp': # untrusted
			extract_media_ips_to_dict(media_ip_dict, 'pim_voice1_ecp', link)
		elif link['id'] == 'pim_voice2_ecp': # trusted
			extract_media_ips_to_dict(media_ip_dict, 'pim_voice2_ecp', link)
		elif link['id'] == 'mate_pim_voice1_ecp': # mate untrusted
			extract_media_ips_to_dict(media_ip_dict, 'mate_pim_voice1_ecp', link)
		elif link['id'] == 'mate_pim_voice2_ecp': # mate trusted
 			extract_media_ips_to_dict(media_ip_dict, 'mate_pim_voice2_ecp', link)
		elif link['id'] == 'scm_oam_ecp': # scm oam
			extract_media_ips_to_dict(media_ip_dict, 'scm_oam_ecp', link, 2)
	log('Extracting PIM untrusted access and trusted core network information is done.')

	media_openstack_info_list = media_instantiation_json_data['vimConnectionInfo']
	log('Extracting cbis information is done.')
	log('Extracting information from media instantiation file is done.')

#################################################################################
def extract_media_ips_to_dict(media_ip_dict, key_str, ext_virtual_link_dict, idx = 0):
	if key_str not in media_ip_dict.keys():
		media_ip_dict[key_str] = []

	log('Extracting media PIM IP addresses for interface {0} is starting...'.format(key_str))
	for i in range(idx + 1):
		media_ip_dict[key_str] += ext_virtual_link_dict['extCps'][i]['cpConfig'][0]['cpProtocolData'][0]['ipOverEthernet']['ipAddresses'][0]['fixedAddresses']
		media_ip_dict[key_str].sort()
	log('Extracting media PIM IP addresses for interface {0} is done.'.format(key_str))

#################################################################################
def check_signaling_subnet():
	global signaling_subnet_list, artifacts_errors_counter
	has_duplex1 = False
	has_duplex2 = False

	pattern = re.compile('10.1{0}.*'.format(str(student_num - 1)))

	log('Checking signaling subnet information...')
	for elem in netconf_ipv4_subnet_list:
		subnet_name = elem.find(ims_lcp_namespace + 'SubnetName').text
		signaling_subnet_list.append(subnet_name)
		log('Checking subnet {0}...'.format(subnet_name))
	
		# MTU size check
		if elem.find(ims_lcp_namespace + 'mtu_size').text != '1500':
			err_log('MTU size of {0} is not 1500'.format(subnet_name) )
			artifacts_errors_counter += 1
		log('MTU size 1500 is ok.')

		# Not check subnet base for h248	
		interface_label = elem.find(ims_lcp_namespace + 'InterfaceLabel').text
		if interface_label == 'bgc0':
			continue

		# Subnet base IP check
		subnet_base = elem.find(ims_lcp_namespace + 'SubnetBase').text
        	if pattern.match(subnet_base) == None:
			err_log('Base IP {0} of subnet {1} does not match design for student {2}'.format(subnet_base, subnet_name, str(student_num)))
			artifacts_errors_counter += 1
		log('Base IP {0} is ok.'.format(subnet_base))

		# For L3 Design, we only have IPv4 subnets
		redundancy = elem.find(ims_lcp_namespace + 'RedundancyMode').text
		if redundancy == 'eipm_acm':
			log('Duplex SRIOV network {0}.'.format(subnet_name))
			if re.match('.*_DUPLEX1', subnet_name):
				has_duplex1 = True
			if re.match('.*_DUPLEX2', subnet_name):
				has_duplex2 = True
		
	# check for total number of signaling subnet 
	if len(signaling_subnet_list) != 8:
		err_log('Subnet numbers of signaling plane should be 8 instead of {0}.'.format(len(signaling_subnet_list)))
		artifacts_errors_counter += 1

	if has_duplex1 != True or has_duplex2 != True:
		err_log('For signaling SRIOV subnet, please use duplex redundancy.')
		artifacts_errors_counter += 1

	log('Checking signaling subnet information is passed.')

#################################################################################
def cnt_ip_per_service_ip_dict(service_ip_dict):
	ip_cnt = 0

	for ni in service_ip_dict:
		for ip_type in service_ip_dict[ni]:
			ip_cnt += len(service_ip_dict[ni][ip_type])

	return ip_cnt

#################################################################################
def check_signaling_service_ip():
	global artifacts_errors_counter
	signaling_ip_cnt = 0
	dfed_dns_ip_num = 0
	x1_ip_num = 0
	x2_ip_num = 0
    
	log('Checking signaling service IP addresses is starting...')
	signaling_ip_cnt += cnt_ip_per_service_ip_dict(netconf_mi_ip_dict) 
	signaling_ip_cnt += len(netconf_ims_ip_list)
	signaling_ip_cnt += cnt_ip_per_service_ip_dict(netconf_feph_ip_dict) 
	signaling_ip_cnt += cnt_ip_per_service_ip_dict(netconf_dfed_ip_dict) 
	signaling_ip_cnt += cnt_ip_per_service_ip_dict(netconf_cnfg_ip_dict) 
	signaling_ip_cnt += cnt_ip_per_service_ip_dict(netconf_cfed_ip_dict) 

	if signaling_ip_cnt != 27:
		err_log('For SBC L3 Design, total number of signaling service IPs should be 27 instead of {0}'.format(signaling_ip_cnt))
		artifacts_errors_counter += 1
	log('Total number of signaling service IPs is 27 - OK.')
	# check for each service 
	# 1. DFED DNS IP number check
	for ni in netconf_dfed_ip_dict:
		if ni == 'dns':
			for ip_type in netconf_dfed_ip_dict[ni]:
				dfed_dns_ip_num += len(netconf_dfed_ip_dict[ni][ip_type])

	if dfed_dns_ip_num != 3:
		err_log('Number of DFED DNS IP should be 3 instead of {0}'.format(dfed_dns_ip_num))
		artifacts_errors_counter += 1
	log('DFED DNS IPs number is 3 - OK.')

	# 2. X1 & X2 IP numbers check
	for ni in netconf_cnfg_ip_dict:
		if ni == 'li_admin':
			for ip_type in netconf_cnfg_ip_dict[ni]:
				x1_ip_num += len(netconf_cnfg_ip_dict[ni][ip_type])
		elif ni == 'li_calldata':
			for ip_type in netconf_cnfg_ip_dict[ni]:
				x2_ip_num += len(netconf_cnfg_ip_dict[ni][ip_type])
	if x1_ip_num != 3:
		err_log('Number of X1 IP should be 3 instead of {0}'.format(x1_ip_num))
 		artifacts_errors_counter += 1
	log('X1 IPs number is 3 - OK.')
	if x2_ip_num != 1:
		err_log('Number of X2 IP should be 1 instead of {0}'.format(x2_ip_num))
		artifacts_errors_counter += 1
	log('X2 IPs number is 1 - OK.')
	log('Checking signaling service IP addresses is done.')

#################################################################################
def check_media_ip():
	global artifacts_errors_counter

	log('Checking media PIM IP addresses is starting...')
	if len(media_ip_dict['pim_voice1_ecp']) != 5:
		err_Log('For PIM unstrusted access subnet, total number of the ip should be 5 instead of {0}'.format(len(media_ip_dict['pim_voice1_ecp'])))
		artifacts_errors_counter += 1
	log('PIM untrusted access subnet IPs number is 5 - OK')
	if len(media_ip_dict['pim_voice2_ecp']) != 5:
		err_Log('For PIM trusted core subnet, total number of the ip should be 5 instead of {0}'.format(len(media_ip_dict['pim_voice2_ecp'])))
 		artifacts_errors_counter += 1
	log('PIM trusted core subnet IPs number is 5 - OK')

	# SRIOV redundancy check
	if media_ip_dict['pim_voice1_ecp'] != media_ip_dict['mate_pim_voice1_ecp']:
		err_log('PIM untrusted access subnet is SRIOV, duplex IPs should be identical.')
		artifacts_errors_counter += 1
	if media_ip_dict['pim_voice2_ecp'] != media_ip_dict['mate_pim_voice2_ecp']:
		err_log('PIM trusted core subnet is SRIOV, duplex IPs should be identical.')
		artifacts_errors_counter += 1
	log('Checking media PIM IP addresses is done.')

#################################################################################
def check_domain_related():
	global artifacts_errors_counter
	dns_ip_list = ['10.1{0}.1.123'.format(str(student_num - 1)), '10.1{0}.2.123'.format(str(student_num - 1))]
	sbc_name = 'pndrasbc1'
	network_domain = 'pandora.net'
	subscriber_home_domain = 'navi.com'

	log('Checking domain related information is starting...')
	configured_dns_ip_list = netconf_basic_information.findall(ims_lcp_namespace + 'DNSServerIPv4Address_DNSDomainName')
	for dns in configured_dns_ip_list:
		if dns.text.split('/')[0] not in dns_ip_list:
			err_log('DNS IP address {0} is not in the given DNS IPs in Design Document.'.format(dns.text))
			artifacts_errors_counter += 1
	log('DNS IPs are ok.')

	configured_local_zone = netconf_basic_information.find(ims_lcp_namespace + 'LocalDNSDomain').text
	local_zone = sbc_name + '.' + network_domain
	if configured_local_zone != local_zone:
		err_log('Network Domain {0} is not same as the given network domain name {1}.'.format(configured_local_zone, local_zone))
		artifacts_errors_counter += 1
	log('DNS domain is ok.')

	configured_sbc_name = netconf_basic_information.find(ims_lcp_namespace + 'SystemName').text
	if configured_sbc_name != sbc_name:
		err_log('SBC name {0} is not same as the given name {1}.'.format(configured_sbc_name, sbc_name))
		artifacts_errors_counter += 1
	log('SBC system name is ok.')

	pattern = re.compile('.*pndrasbc1.*')
	configured_cfed_external_hostname = netconf_cfed_port_table_record.find(isbc_sig_namespace + 'EXTERNAL_HOST_NAME').text
	if pattern.match(configured_cfed_external_hostname) == None:
		err_log('External host name {0} does not contain SBC name {1}'.format(configured_cfed_external_hostname, sbc_name))
		artifacts_errors_counter += 1
	log('CFED external hostname is ok.')

	configured_home_domain = netconf_ngss_parameters.find(isbc_sig_namespace + 'DEFAULTHOMEDOMAIN').text
	if configured_home_domain != subscriber_home_domain:
		err_log('Subscriber home domain {0} is not same as the given domain name {1}.'.format(configured_home_domain, subscriber_home_domain))
		artifacts_errors_counter += 1
	log('Home domain is ok.')
	log('Checking domain related information is done.')

#################################################################################
def check_interconnection():
	global artifacts_errors_counter
	icscf_fqdn = 'icscf.pandora.net:5070'
	diameter_rx_fqdn = 'pcrf.pandora.net'
	diameter_rf_fqdn = 'ccf.pandora.net'

	log('Checking interconnection related information is starting...')
	# check icscf fdqn
	cmdline = 'cat {0} | grep {1}'.format(signaling_netconf_xml, icscf_fqdn)
	if run_cmd_with_ret_code(cmdline) == False:
        	err_log('No ICSCF is configured.')
        	artifacts_errors_counter += 1
	log('ICSCF is ok.')

    	# check diameter rx
	cmdline = 'cat {0} | grep {1}'.format(signaling_netconf_xml, diameter_rx_fqdn)
	if run_cmd_with_ret_code(cmdline) == False:
		err_log('No diameter rx profile FQDN is configured.')
		artifacts_errors_counter += 1
	log('Diameter Rx profile is ok.')

	# check diameter rf
	cmdline = 'cat {0} | grep {1}'.format(signaling_netconf_xml, diameter_rf_fqdn)
	if run_cmd_with_ret_code(cmdline) == False:
		err_log('No diameter rf profile FQDN is configured.')
		artifacts_errors_counter += 1
	log('Diameter Rf profile is ok.')
	log('Checking interconnection related information is done.')

#################################################################################
def check_sbc_feature():
	global artifacts_errors_counter
	scscf_fqdn = 'scscf.pandora.net'
	golden_codec_list = []
	stn_sr = '9881234500{0}'.format(str(student_num))

	log('Checking sbc feature related information is starting...')
	# SIP DSCP should be 48
	sip_dscp = netconf_ngss_parameters.find(isbc_sig_namespace + 'SIPDIFFSERVCODEPOINT').text
	if sip_dscp != '48':
		err_log('SIP DSCP value should be 48, but configured value is {0}'.format(sip_dscp))
		artifacts_errors_counter += 1
	log('SIP DSCP is 48 - OK.')

	support_media_negotiation = netconf_sblp_table_record.find(isbc_sig_namespace + 'MediaNegotiationOptions').find(isbc_sig_namespace + 'MEDIA_NEGOTIATION_SUPPORT').text	
	if support_media_negotiation == 'No':
		err_log('For media transcoding capability, support media negotiation should be configured as Yes.')
		artifacts_errors_counter += 1
	log('Support media negotiation is enabled.')
	
	support_ipsec = netconf_pcscf_profile_table_record.find(isbc_sig_namespace + 'SECURE_SERVER_PORT').text
	if support_ipsec == '0':
		err_log('SBC need to support IPsec.')
		artifacts_errors_counter += 1
	log('Support IPsec is enabled.')

	# signaling sdp profile check
	golden_codec_obj_list = netconf_sdp_profile_table_record.find(isbc_sig_namespace + 'GoldenCodecSet').findall(isbc_sig_namespace + 'GOLDEN_CODEC')
	for codec in golden_codec_obj_list:
		golden_codec_list.append(codec.text)

	if ('PCMU' not in golden_codec_list) and ('PCMA' not in golden_codec_list):
		err_log('PCMA or PCMA should be in signaling golden codec list.')
		artifacts_errors_counter += 1
	if 'AMR' not in golden_codec_list:
        	err_log('AMR is not found in signaling golden codec list.')
        	artifacts_errors_counter += 1
    	if 'AMR-WB' not in golden_codec_list:
        	err_log('AMR-WB is not found in signaling golden codec list.')
        	artifacts_errors_counter += 1
    	if 'G729' not in golden_codec_list:
        	err_log('G729 is not found in signaling golden codec list.')
        	artifacts_errors_counter += 1
	log('Signaling codec list is ok.')

	# media capacity profile codec list check
	if 'g711' not in media_codec_list:
		err_log('G711 is not found in media codec list.')
		artifacts_errors_counter += 1
	if 'amr2' not in media_codec_list:
        	err_log('AMR is not found in media codec list.')
        	artifacts_errors_counter += 1
    	if 'amr-wb' not in media_codec_list:
        	err_log('AMR-WB is not found in media codec list.')
        	artifacts_errors_counter += 1
    	if 'g729' not in media_codec_list and 'g729a' not in media_codec_list:
        	err_log('G729 is not found in media codec list.')
        	artifacts_errors_counter += 1
	log('Media codec capacity is ok.')
	
	log('Checking eSRVCC related features.')
    	# eSRVCC check 1 - support ATCF
	support_atcf = netconf_pcscf_profile_table_record.find(isbc_sig_namespace + 'SUPPORT_ATCF').text
	if support_atcf == 'No':
		err_log('To support eSRVCC, ATCF should be enabled.')
		artifacts_errors_counter += 1
	log('Support ATCF is enabled.')
    	# eSRVCC check 2 - spareRecords table assignement type and SPARE8
    	spare_records_tbl_assign_type = netconf_spare_records_table_record.find(isbc_sig_namespace + 'ASSIGNMENT_TYPE').text
    	if spare_records_tbl_assign_type != 'NGSS Parameters':
        	err_log('For eSRVCC, assignment type in spare records table should be NGSS Parameters.')
        	artifacts_errors_counter += 1
	log('Spare record table assignment type is NGSS Parameter - OK.')
    	spare8 = netconf_spare_records_table_record.find(isbc_sig_namespace + 'SPARE8').text
    	if spare8 != 'Yes':
        	err_log('For eSRVCC, SPARE8 in spare records table should be Yes.')
        	artifacts_errors_counter += 1
	log('SPARE8 is Yes.')

	configured_stn_sr = netconf_stn_sr_table_record.find(isbc_sig_namespace + 'STN_SR_IDENTIFIER').text
	if configured_stn_sr != stn_sr:
		err_log('STN-SR {0} is not same as the given value {1}.'.format(configured_stn_sr, stn_sr))
		artifacts_errors_counter += 1
	log('STN-SR is ok.')
	log('Checking eSRVCC related features is done.')
	log('Checking sbc feature related information is done.')

#################################################################################
def check_timezone_ntp():
	global artifacts_errors_counter
	country_code = '988'
	time_zone = 'UTC'
	ntp_server_list = ['10.1{0}.1.100'.format(str(student_num - 1)), '10.1{0}.2.100'.format(str(student_num - 1))]

	log('Checking timezone related information is starting...')
	configured_country_code = netconf_global_parameters.find(isbc_sig_namespace + 'COUNTRYCODE').text
	if configured_country_code != country_code:
		err_log('Country code {0} is not same as the given one {1}.'.format(configured_country_code, country_code))
		artifacts_errors_counter += 1
	log('Country code is ok.')

	configured_time_zone = netconf_basic_information.find(ims_lcp_namespace + 'TimeZone').text
	if configured_time_zone != time_zone:
		err_log('Timezone {0} is not same as the given timezone {1}.'.format(configured_time_zone, time_zone))
		artifacts_errors_counter += 1
	log('Timezone is ok.')

	configured_ntp_server_list = netconf_basic_information.findall(ims_lcp_namespace + 'NTPServerIPv4Address')
	for ntp in configured_ntp_server_list:
		if ntp.text not in ntp_server_list:
			err_log('NTP server IP address {0} is not in the given NTP IPs in Designe Document.'.format(ntp.text))
			artifacts_errors_counter += 1
	log('NTP servers are ok.')
	log('Checking timezone related information is done.')

#################################################################################
def check_cloud_information():
	global artifacts_errors_counter
	openstack_version = 'Queens'
	network_service = 'Nsip'
	interface_endpoint = 'https://10.1{0}.8.8:13000/v3'.format(str(student_num - 1))
	nova_zone = 'zone1'
	storage_zone = 'nova'
	vol_storage_type = 'tripleo-raid'
	sig_vm_flavor_list = ['SBC_OAM', 'SBC_SC', 'SBC_FW', 'SBC_BGC', 'SBC_CFED', 'SBC_DFED']
    	media_vm_flavor_list = ['SBC_SCM', 'SBC_PIM', 'SBC_MCM']

	log('Checking cloud related information is starting...')

	configured_openstack_version = netconf_basic_information.find(ims_lcp_namespace + 'openstack_version').text
    	if configured_openstack_version != openstack_version:
        	err_log('Openstack version {0} is not same as the given version {1}'.format(configured_openstack_version, openstack_version))
        	artifacts_errors_counter += 1
	log('Openstack version is ok.')

	configured_network_service = netconf_basic_information.find(ims_lcp_namespace + 'NetworkServiceType').text
    	if configured_network_service != network_service:
        	err_log('Network service {0} is not same as the given value {1}'.format(configured_network_service, network_service))
        	artifacts_errors_counter += 1
	log('Network service type is ok.')
	
	if check_openstack_access_info('region', 'regionOne') == True:
		log('Openstack region is ok.')
	else:
		artifacts_errors_counter += 1

	if check_openstack_access_info('username', 'sbcuser') == True:
		log('Openstack username is ok.')
	else:
		artifacts_errors_counter += 1

	if check_openstack_access_info('project', 'SBC_DESIGN') == True:
		log('Openstack project name is ok.')
	else:
		artifacts_errors_counter += 1

	if check_openstack_access_info('userDomain', 'Default') == True:
		log('Openstack user domain is ok.')
	else:
		artifacts_errors_counter += 1

	if check_openstack_access_info('projectDomain', 'default') == True:
		log('Openstack project domain is ok.')
	else:
		artifacts_errors_counter += 1

	if check_openstack_access_info('interfaceEndpoint', interface_endpoint) == True:
		log('Openstack interface endpoint is ok.')
	else:
		artifacts_errors_counter += 1

	configured_side0_zone = netconf_cloud_deploy_info.find(ims_lcp_namespace + 'side0_availability_zone').text
	configured_side1_zone = netconf_cloud_deploy_info.find(ims_lcp_namespace + 'side1_availability_zone').text
	if configured_side0_zone != configured_side1_zone:
		err_log('Both side0 and side1 availability zone should be same.')
		artifacts_errors_counter += 1
	else:
		if configured_side0_zone != nova_zone:
			err_log('Signaling nova zone {0} is not same as given zone {1}.'.format(configured_side0_zone, nova_zone))
			artifacts_errors_counter += 1

	configured_side0_storage_zone = netconf_cloud_deploy_info.find(ims_lcp_namespace + 'side0_storage_zone').text
	configured_side1_storage_zone = netconf_cloud_deploy_info.find(ims_lcp_namespace + 'side1_storage_zone').text
	if configured_side0_storage_zone != configured_side1_storage_zone:
		err_log('Both side0 and side1 storage zone should be same.')
		artifacts_errors_counter += 1
	else:
		if configured_side0_storage_zone != storage_zone:
			err_log('Signaling storage zone {0} is not same as given zone {1}.'.format(configured_side0_storage_zone, storage_zone))
			artifacts_errors_counter += 1

	for zone in media_instantiation_json_data['zones']:
		if re.match('.*storage.*', zone['id']) != None:
			if zone['zoneId'] != storage_zone:
				err_log('Media storage zone {0} is not same as given zone {1}.'.format(zone['zoneId'], storage_zone))
				artifacts_errors_counter += 1
		else:
			if zone['zoneId'] != nova_zone:
				err_log('Media nova zone {0} is not same as given zone {1}.'.format(zone['zoneId'], nova_zone))
				artifacts_errors_counter += 1
	log('Both Openstack nova zone and storage zone are ok.')


	configured_vol_storage_type = netconf_cloud_deploy_info.find(ims_lcp_namespace + 'storagevol_type').text
	if configured_vol_storage_type != vol_storage_type:
		err_log('Volume storage type {0} is not same as the given type {1}.'.format(configured_vol_storage_type, vol_storage_type))
		artifacts_errors_counter += 1
	log('Siganling storage volume is ok.')

	configured_vm_group_info_list = netconf_cloud_deploy_info.findall(ims_lcp_namespace + 'vm_group_information')
	for vm_group in configured_vm_group_info_list:
		side0_flavor = vm_group.find(ims_lcp_namespace + 'side0_flavor').text
		side1_flavor = vm_group.find(ims_lcp_namespace + 'side1_flavor').text
		if side0_flavor != side1_flavor:
			err_log('Both side0 and side1 flavor should be same.')
			artifacts_errors_counter += 1

		if side0_flavor not in sig_vm_flavor_list:
			err_log('Flavor name {0} is not valid one, please refer to design.'.format(side0_flavor))
			artifacts_errors_counter += 1

    	for media_flavor in media_flavor_list:
        	if media_flavor not in media_vm_flavor_list:
            		err_log('The media flavor {0} is incorrect, please refer to design.'.format(media_flavor))
            		artifacts_errors_counter += 1
	log('Openstack VM flavors are ok.')
	
	log('Checking cloud related information is done.')

def check_openstack_access_info(keyStr, expected_val):
	media_val = ''

	signaling_val = netconf_cbam_info_vims.find(ims_lcp_namespace + keyStr).text
	if signaling_val != expected_val:
		err_log('In signaling artifact, {0} {1} is not same as the value {2} in design.'.format(keyStr, signaling_val, expected_val))
		return False

	if keyStr == 'interfaceEndpoint':
		media_val = media_openstack_info_list[0]['interfaceInfo']['endpoint']
	else:
		media_val = media_openstack_info_list[0]['accessInfo'][keyStr]

	if media_val != expected_val:
		err_log('In media artifact, {0} {1} is not same as the value {2} in design.'.format(keyStr, media_val, expected_val))
		return False
	
	return True
#################################################################################
def main():
	log('SBC Design certificate work assignment assessment tool start running...')
	parse_validate_opts()
	
	if os.path.exists(assessment_log_file) == True:
		cmdline = '/usr/bin/rm -rf ' + assessment_log_file
		try:
			(output, error) = run_cmd_with_std_error(cmdline)
		except Exception, exc:
			log(str(exc))

	signaling_artifact_process()
	media_artifact_process()

	load_signaling_artifacts()
	load_media_artifacts()

	extract_netconfprov_xml_info(signaling_netconf_xml_data)
	extract_media_instantiation_info(media_instantiation_json_data)

	check_signaling_subnet()

	check_signaling_service_ip()
	check_media_ip()

	check_domain_related()
	check_interconnection()
	check_sbc_feature()
	check_timezone_ntp()
	check_cloud_information()
  
	if artifacts_errors_counter == 0:	
		log('The design assignment validation is passed. Congrats!')
    		sys.exit(PASS)
	else:
		err_log('Total {0} errors found in artifacts. The design does not meet requirement.'.format(artifacts_errors_counter))
		sys.exit(FAIL)

if __name__ == '__main__':
    main()

