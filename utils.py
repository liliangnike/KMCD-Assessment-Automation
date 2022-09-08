import os
import sys
import stat
import re
import pdb
import socket  
import commands
import traceback
import platform
import shutil
import optparse 
import exceptions
import subprocess
import ctypes
import copy
from subprocess import Popen, PIPE
from time import gmtime, strftime


# There are four debugging levels(1, 2, 3, 4), 1 is min level, 4 is max level, default is 3	
DEBUGGING = 3
DBG_STREAM = sys.stdout	

# Global variables
assessment_log_file = '/tmp/sbc_design/assessment.log'
assessment_log_path = '/tmp/sbc_design/'


################################################################################	
def log(msg):
	''' Module to use send log messages into log file and log is printed to stdout as well '''
	global assessment_log_file, assessment_log_path
	
	try:
		if os.path.exists(assessment_log_path) == False:
			print 'log path = ', assessment_log_path
			raise Exception, 'Error: log path does not exist'

		f = open(assessment_log_file,"a")
		dt = strftime("%h %d %T ",gmtime())

		f.write(dt)		# date
		f.write(' ')
		f.write(msg)		# The message
		f.write('\n')
		f.close()
		
		# during transition, print to stdout as well, so that log and standard message can coexist. 
		print  msg
		
	except Exception, exc:
		print exc # str(exc) is printed
		raise Exception, 'log() failed'
		
################################################################################		
def log_only(msg):
	''' Module to use send log messages into log '''
	global assessment_log_file, assessment_log_path
	
	try:
		if os.path.exists(assessment_log_path) == False:
			print 'log path = ', assessment_log_path
			raise Exception, 'Error: log path does not exist'

		f = open(assessment_log_file,"a")
		dt = strftime("%h %d %T ",gmtime())
		line = dt + ' ' + msg + '\n'
		f.write(line)
		f.close()
		
	except Exception, exc:
		print exc # str(exc) is printed
		raise Exception, 'log() failed'
		
################################################################################		
def err_log(msg):
	''' Module to use send error messages into growth/degrowth log'''
	global assessment_log_file, assessment_log_path
	
	try:
		if os.path.exists(assessment_log_path) == False:
			print 'log path = ', assessment_log_path
			raise Exception, 'Error: log path does not exist'

		f = open(assessment_log_file, "a")
		dt = strftime("%h %d %T ",gmtime())
		line = dt + ' ERROR: ' + msg + '\n'
		f.write(line)
		f.close()
		
		# during transition, print to stdout as well, so that log and standard message can coexist. 
		print  "ERROR: " + msg
		
	except Exception, exc:
		print exc # str(exc) is printed
		raise Exception, 'err_log() failed'
 
################################################################################
def run_cmd_with_std_error( cmd, err_log_flag = True ):
	pobj = subprocess.Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
	# Read data from stdout and stderr of child process via pipe, until end-of-file is reached. 
	# Wait for process to terminate.	
	(output, error) = pobj.communicate()
	# Check if child process has terminated. Set and return returncode attribute.	
	status = pobj.poll()
	if status !=0 :
		if err_log_flag == True:
			err_log('Failed to execute {0}.'.format(cmd))
		raise Exception, error
	else:
		return (output, error)	
		
################################################################################
def run_cmd_with_std_output( cmd ):
	pobj = subprocess.Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
	# Read data from stdout and stderr of child process via pipe, until end-of-file is reached. 
	# Wait for process to terminate.
	(output, error) = pobj.communicate()
	# Check if child process has terminated. Set and return returncode attribute.
	status = pobj.poll()
	if status !=0 :
		err_log('Failed to execute {0}.'.format(cmd))
		raise Exception, output
	else:
		return (output, error)

################################################################################
def run_cmd_with_ret_code( cmd ):
	''' Runs a shell command, and returns its exit code. '''
	status = subprocess.call(cmd, shell=True)
	if status != 0:
		return False
	else:
		return True
  
################################################################################		
def debug (level, msg):
	global DEBUGGING
	global DBG_STREAM
	if DEBUGGING < level and DBG_STREAM:
		DBG_STREAM.write (msg + '\n')	

################################################################################
def get_ip_offset(ip, base):
	''' Get offset based on ip base. Assume ip and base in same subnet.'''
	intip = ip2int(ip)
	intbase = ip2int(base)
	offset = intip - (intip & intbase)
	return offset
	
################################################################################
def ip2int(ip):
	''' Covert ip string to integer. '''
	ip_list = []
	ip_list = ip.split('.')
	return (int(ip_list[0])<<24) | (int(ip_list[1])<<16) | (int(ip_list[2])<<8) | int(ip_list[3])

################################################################################
def is_last_ip_used_as_gateway(gw_ip, base, mask):
	mask_offset = get_ip_offset('255.255.255.255', mask)
	
	gw_offset = get_ip_offset(gw_ip, base)

	if gw_offset != mask_offset:
		return False
	else:
		return True

