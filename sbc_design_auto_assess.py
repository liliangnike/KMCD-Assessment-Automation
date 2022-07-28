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

ims_lcp_namespace = '{http://nokia.com/yang/IMS/LCP}'
isbc_sig_namespace = '{http://nokia.com/yang/isbc-sig}'

# global XML element objects to save netconf information
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
media_network_list = []
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
	# TODO -- consider to add exam level (L3, L4...) and cloud product (openstack, cnf) later

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

	(signaling_instantiation_json, error) = run_cmd_with_std_output('find ' + signaling_artifact_path + ' -name bulk_adm')
	signaling_instantiation_json = signaling_instantiation_json.strip('\n') + '/LCM_instantiate_params.json'

	(signaling_netconf_xml, error) = run_cmd_with_std_output('find ' + signaling_artifact_path + ' -name bulk_netconf')
	signaling_netconf_xml = signaling_netconf_xml.split('\n')[1] + '/netconfprov_artifact.xml'

def load_signaling_artifacts():
	global signaling_instantiation_json_data, signaling_netconf_xml_data
	global netconf_ipv4_subnet_list
	global netconf_pcscf_profile_table, netconf_pcscf_profile_table_record
	global netconf_basic_information
	global netconf_cfed_port_table, netconf_cfed_port_table_record
	global netconf_pnaptr_table, netconf_pnaptr_table_record
	global netconf_sblp_table, netconf_sblp_table_record
	global netconf_stn_sr_table_record
	global netconf_global_parameters
	global netconf_cbam_information, netconf_cbam_info_vims
	global netconf_cloud_deploy_info

	# Parse signaling instantiation json file
        with open(signaling_instantiation_json, 'r') as sigaling_file:
        	signaling_instantiation_json_data = json.load(sigaling_file)

	# Parse XML
	tree = ET.parse(signaling_netconf_xml)
	signaling_netconf_xml_data = tree.getroot()

	# Save information
	netconf_ipv4_subnet_list = signaling_netconf_xml_data.findall(ims_lcp_namespace + 'IPv4SubnetInformation')
	netconf_pcscf_profile_table = signaling_netconf_xml_data.find(isbc_sig_namespace + 'PcscfProfileTable')
	netconf_pcscf_profile_table_record  = netconf_pcscf_profile_table.find(isbc_sig_namespace + 'Record')
	netconf_basic_information = signaling_netconf_xml_data.find(ims_lcp_namespace + 'BasicInformation')
     	netconf_cfed_port_table = signaling_netconf_xml_data.find(isbc_sig_namespace + 'CFEDPortTable').find(isbc_sig_namespace + 'Record')  
     	netconf_cfed_port_table_record = netconf_cfed_port_table.find(isbc_sig_namespace + 'Record')  
	netconf_pnaptr_table = signaling_netconf_xml_data.find(isbc_sig_namespace + 'PNAPTRTargetURITable')
	netconf_pnaptr_table_record = netconf_pnaptr_table.find(isbc_sig_namespace + 'Record')
	netconf_sblp_table = signaling_netconf_xml_data.find(isbc_sig_namespace + 'SblpProfileTable')
	netconf_sblp_table_record = netconf_sblp_table.find(isbc_sig_namespace + 'Record')
	netconf_stn_sr_table_record = signaling_netconf_xml_data.find(isbc_sig_namespace + 'STNSRTable').find(isbc_sig_namespace + 'Record')
	netconf_global_parameters = signaling_netconf_xml_data.find(isbc_sig_namespace + 'GlobalParameters')
	
	netconf_cbam_information = signaling_netconf_xml_data.find(ims_lcp_namespace + 'cbam_information')
	netconf_cbam_info_vims = netconf_cbam_information.find(ims_lcp_namespace + 'vims')
	
	netconf_cloud_deploy_info = signaling_netconf_xml_data.find(ims_lcp_namespace + 'cloud_deployment_information')

def load_media_artifacts():
	global media_instantiation_json_data, media_mgw_yaml_data 
	
	# Parse media instantiation json file
	media_instantiation_json
	with open(media_instantiation_json, 'r') as media_file:
		media_instantiation_json_data = json.load(media_file)

def check_signaling_subnet():
	global signaling_subnet_list

	pattern_oam = re.compile('.*oam.*', re.IGNORECASE)

	for elem in netconf_ipv4_subnet_list:
		subnet_name = elem.find(ims_lcp_namespace + 'SubnetName').text
		signaling_subnet_list.append(subnet_name)
	
		# 1. MTU size check
		if elem.find(ims_lcp_namespace + 'mtu_size').text != '1500':
			err_log('MTU size of {0} is not 1500'.format(subnet_name) )
			sys.exit(FAIL)
	
		# 3. OAM network IP validation
		if pattern_oam.match(subnet_name):
			oam_subnet_base = elem.find(ims_lcp_namespace + 'SubnetBase').text
			if oam_subnet_base != '10.10.10.96':
				err_log('OAM subnet base should be 10.10.10.96.')
				sys.exit(FAIL)

			oam_gateway = elem.find(ims_lcp_namespace + 'SubnetGateway').text
			if oam_gateway != '10.10.10.126':
				err_log('OAM subnet gateway should be 10.10.10.126.')
				sys.exit(FAIL)

		# 4. check external subnet gateways
		gateway = elem.find(ims_lcp_namespace + 'SubnetGateway').text
		base = elem.find(ims_lcp_namespace + 'SubnetBase').text
		mask = elem.find(ims_lcp_namespace + 'SubnetNetworkMask').text
		if is_last_ip_used_as_gateway(gateway, base, mask) == False:
			err_log('Gateway of subnet {0} is not last available IP'.format(subnet_name))
			sys.exit(FAIL)

	# 2. Name check
	if len(signaling_subnet_list) < 5:
		err_log('Subnet numbers of signaling plane should be no less than 5.')
		sys.exit(FAIL)

	pattern = re.compile('.*oam.*|.*gm.*|.*mw.*|.*rx.*|.*rf.*', re.IGNORECASE)
	for net in signaling_subnet_list:
		if pattern.match(net) == None:
			err_log('The subnet {0} is not in the name list as required in SBC L3 design assignment doc'.format(net) )		

			
	# 5. SIP DSCP should be 48
	sip_dscp = netconf_pcscf_profile_table_record.find(isbc_sig_namespace + 'SIP_DSCP_FOR_GM').text
	if sip_dscp != 48:
		err_log('SIP DSCP value should be 48, but configured value is {0}'.format(sip_dscp))
		sys.exit(FAIL)

def check_media_subnet():
	global media_pim_subnet_list, media_network_list
	mb_network_nums = 0

	pattern1 = re.compile('.*h248.*', re.IGNORECASE)
	pattern2 = re.compile('.*oam.*', re.IGNORECASE)

	# for differ SBC release, instantiation json file might be different
	if sbc_release == 'R20.0':
		# 1. access and core networks should be defined. They are also duplex.
		# If need to match name to check, will do in future
		for net in media_instantiation_json_data['extVirtualLinks']:
			if pattern1.match(net['resourceId']) == None and pattern2.match(net['resourceId']) == None:
				mb_network_nums += 1

		if mb_network_nums < 4:
			err_log('Mb interface for access and core should be defined as different network. Both are duplex.')
			sys.exit(FAIL)

		# 2. check PIM ip numbers for future growth - TODO
		if len (media_instantiation_json_data['extVirtualLinks'][0]['extCps'][0]['addresses'][0]['ip']) < 3:
			err_log('Need to support to grow PIM pairs to 3.')
                        sys.exit(FAIL)

def check_domain_related():
	dns_ip_list = ['10.10.1.123', '10.10.2.123']
	network_domain = 'pandora.net'
	sbc_name = 'pndrasbc1'
	subscriber_home_domain = 'navi.com'

	configured_dns_ip_list = netconf_basic_information.findall(ims_lcp_namespace + 'DNSServerIPv4Address_DNSDomainName')
	for dns in configured_dns_ip_list:
		if dns.text not in dns_ip_list:
			err_log('DNS IP address {0} is not in the given DNS IPs in Designe Document.'.format(dns.text))
			sys.exit(FAIL)

	configured_dns_domain = netconf_basic_information.find(ims_lcp_namespace + 'LocalDNSDomain').text
	if configured_dns_domain != network_domain:
		err_log('Network Domain {0} is not same as the given network domain name {1}.'.format(configured_dns_domain, network_domain))
		sys.exit(FAIL)

	configured_sbc_name = netconf_basic_information.find(ims_lcp_namespace + 'SystemName').text
	if configured_sbc_name != sbc_name:
		err_log('SBC name {0} is not same as the given name {1}.'.format(configured_sbc_name, sbc_name))
		sys.exit(FAIL)

	pattern = re.compile('.*pndrasbc1.*')
	configured_cfed_external_hostname = netconf_cfed_port_table_record.find(isbc_sig_namespace + 'EXTERNAL_HOST_NAME').text
	if pattern.match(configured_cfed_external_hostname) == None:
		err_log('External host name {0} does not contain SBC name {1}'.format(configured_cfed_external_hostname, sbc_name))
		sys.exit(FAIL)

def check_interconnection():
	icscf_fqdn = 'icscf.pandora.net:5070'

	configured_icscf = netconf_pnaptr_table_record.find(isbc_sig_namespace + 'TARGET_URI').text
	if configured_icscf != icscf_fqdn:
		err_log('ICSCF in PNAPTR table is {0}, that is not same as the given value {1}.'.format(configured_icscf, icscf_fqdn))
		sys.exit(FAIL)

def check_sbc_feature():
	scscf_fqdn = 'scscf.pandora.net'
	stn_sr = '98812345000'

	support_media_negotiation = netconf_sblp_table_record.find(isbc_sig_namespace + 'MediaNegotiationOptions').find(isbc_sig_namespace + 'MEDIA_NEGOTIATION_SUPPORT').text	
	if support_media_negotiation == 'No':
		err_log('For media transcoding capability, support media negotiation should be configured as Yes.')
		sys.exit(FAIL)
	
	support_ipsec = netconf_pcscf_profile_table_record.find(isbc_sig_namespace + 'SUPPORT_ONLY_IPSEC_CAPABLE').text
	if support_ipsec == 'No':
		err_log('SBC need to support IPsec.')
		sys.exit(FAIL)


	emergency_host_uri = netconf_pcscf_profile_table_record.find(isbc_sig_namespace + 'EMERGENCYHOSTURI').text
	if emergency_host_uri != 'No':
		err_log('Emergency call should be routed to SCSCF {0}, but configured value is {1}.'.format(scscf_fqdn, emergency_host_uri))
		sys.exit(FAIL)

	
	support_atcf = netconf_pcscf_profile_table_record.find(isbc_sig_namespace + 'SUPPORT_ATCF').text
	if support_atcf == 'No':
		err_log('To support eSRVCC, ATCF should be enabled.')
		sys.exit(FAIL)


	configured_stn_sr = netconf_stn_sr_table_record.find(isbc_sig_namespace + 'STN_SR_IDENTIFIER').text
	if configured_stn_sr != stn_sr:
		err_log('STN-SR {0} is not same as the given value {1}.'.format(configured_stn_sr, stn_sr))
		sys.exit(FAIL)

def check_timezone_ntp():
	country_code = '998'
	time_zone = 'UTC'
	ntp_server_list = ['10.10.1.100', '10.10.2.100']

	configured_country_code = netconf_global_parameters.find(isbc_sig_namespace + 'COUNTRYCODE').text
	if configured_country_code != country_code:
		err_log('Country code {0} is not same as the given one {1}.'.format(configured_country_code, country_code))
		sys.exit(FAIL)

	configured_time_zone = netconf_basic_information.find(ims_lcp_namespace + 'TimeZone').text
	if configured_time_zone != time_zone:
		err_log('Timezone {0} is not same as the given timezone {1}.'.format(configured_time_zone, time_zone))
		sys.exit(FAIL)

	configured_ntp_server_list = netconf_basic_information.findall(ims_lcp_namespace + 'NTPServerIPv4Address')
	for ntp in configured_ntp_server_list:
		if ntp.text not in ntp_server_list:
			err_log('NTP server IP address {0} is not in the given NTP IPs in Designe Document.'.format(ntp.text))
			sys.exit(FAIL)

def check_cloud_information():
	region_name = 'regionOne'
	tenant = 'SBC'
	interface_endpoint = 'https://10.10.8.8:13000'
	username = 'sbcuser'
	nova_zone = 'zone1'
	storage_zone = 'nova'
	vol_storage_type = 'tripleo-ceph'
	sig_vm_flavor_list = ['SBC_OAM', 'SBC_SC', 'SBC_FW', 'SBC_BGC', 'SBC_CFED', 'SBC_DFED']

	configured_region_name = netconf_cbam_info_vims.find(ims_lcp_namespace + 'region').text
	if configured_region_name != region_name:
		err_log('Region {0} is not same as the given region name {1}.'.format(configured_region_name, region_name))
		sys.exit(FAIL)

	configured_tenant = netconf_cbam_info_vims.find(ims_lcp_namespace + 'tenant').text
	if configured_tenant != tenant:
		err_log('Tenant name {0} is not same as the given tenant name {1}.'.format(configured_tenant, tenant))
		sys.exit(FAIL)
	
	configured_interface_endpoint = netconf_cbam_info_vims.find(ims_lcp_namespace + 'interfaceEndpoint').text
	if configured_interface_endpoint != interface_endpoint:
		err_log('Interface endpoint {0} is not same as the given interface endpoint {1}.'.format(configured_interface_endpoint, interface_endpoint))
		sys.exit(FAIL)

	configured_username = netconf_cbam_info_vims.find(ims_lcp_namespace + 'username').text
	if configured_username != username:
		err_log('User name {0} is not same as the given user name {1}.'.format(configured_username, username))
		sys.exit(FAIL)

	configured_side0_zone = netconf_cloud_deploy_info.find(ims_lcp_namespace + 'side0_availability_zone').text
	configured_side1_zone = netconf_cloud_deploy_info.find(ims_lcp_namespace + 'side1_availability_zone').text
	if configured_side0_zone != configured_side1_zone:
		err_log('Both side0 and side1 availability zone should be same.')
		sys.exit(FAIL)
	else:
		if configured_side0_zone != nova_zone:
			err_log('Nova zone {0} is not same as given zone {1}.'.format(configured_side0_zone, nova_zone))
			sys.exit(FAIL)

	configured_side0_storage_zone = netconf_cloud_deploy_info.find(ims_lcp_namespace + 'side0_storage_zone').text
	configured_side1_storage_zone = netconf_cloud_deploy_info.find(ims_lcp_namespace + 'side1_storage_zone').text
	if configured_side0_storage_zone != configured_side1_storage_zone:
		err_log('Both side0 and side1 storage zone should be same.')
		sys.exit(FAIL)
	else:
		if configured_side0_storage_zone != storage_zone:
			err_log('Storage zone {0} is not same as given zone {1}.'.format(configured_side0_storage_zone, storage_zone))
			sys.exit(FAIL)

	configured_vol_storage_type = netconf_cloud_deploy_info.find(ims_lcp_namespace + 'storagevol_type').text
	if configured_vol_storage_type != vol_storage_type:
		err_log('Volume storage type {0} is not same as the given type {1}.'.format(configured_vol_storage_type, vol_storage_type))
		sys.exit(FAIL)

	configured_vm_group_info_list = netconf_cloud_deploy_info.findall(ims_lcp_namespace + 'vm_group_information')
	for vm_group in configured_vm_group_info_list:
		side0_flavor = vm_group.find(ims_lcp_namespace + 'side0_flavor').text
		side1_flavor = vm_group.find(ims_lcp_namespace + 'side1_flavor').text
		if side0_flavor != side1_flavor:
			err_log('Both side0 and side1 flavor should be same.')
			sys.exit(FAIL)

		if side0_flavor not in sig_vm_flavor_list:
			err_log('Flavor name {0} is not valid one, please refer to L3 design document.'.format(side0_flavor))
			sys.exit(FAIL)
	# TODO - check SBC_SCM, SBC_PIM, SBC_MCM

#################################################################################
def main():
        parse_validate_opts()
        signaling_artifact_process()
        media_artifact_process()
        load_signaling_artifacts()
        load_media_artifacts()
	check_signaling_subnet()
	check_media_subnet()
        check_domain_related()
        check_interconnection()
        check_sbc_feature()
        check_timezone_ntp()
        check_cloud_information()
  	
	sys.exit(PASS)

if __name__ == '__main__':
        main()

