#!/bin/bash

#############################################################
#
#    Description: Script tool to assess work assignement for 
#                 SBC L3 Design exam.
#                 
#    Author     : Shawn Li
#    Company    : Nokia 
#
#############################################################

typeset THIS=${0##*/}
typeset CURR_CMD="${THIS} ${@}"
typeset USER=$(whoami)

# Error return value check list
GETOPT_EXE_ERROR=2

# Global Variables
typeset SIG_ARTIFACTS_ZIP=""
typeset MEDIA_ARTIFACTS_ZIP=""
typeset SBC_RELEASE=""
typeset SIG_UNZIP_TARGET_PATH="/tmp/sbc_design/signaling"
typeset MEDIA_UNZIP_TARGET_PATH="/tmp/sbc_design/media"

# Global commands set
typeset UNZIP="/usr/bin/unzip"
typeset MKDIR="/usr/bin/mkdir"
typeset RM="/usr/bin/rm"

GENERAL_USAGE="USAGE:
${THIS} < --help | --examples >
  or
${THIS} --signaling-artifacts <Signaling Artifacts Zip file> --media-artifacts <Media Artifacts Zip file> --release <SBC Release>"

EXTENDED_USAGE="${GENERAL_USAGE}

Where,

--help - shows extended usage

--examples - shows some example usages.

--signaling-artifacts - Signaling Artifacts Zip file

--media-artifacts - Media Artifacts Zip file

--release - SBC Release

"

EXAMPLES="
EXAMPLES:

${THIS} --signaling-artifacts /tmp/SBC-signaling_R21.8MP2110 --media-artifacts /tmp/nokia.vMGW_C218_M_O_av100043.OpenStack_CBAM.B02 --release R21.8MP2110

"
function parse_opts
{
    typeset -i val=0

    if (( ${#} <= 0 )); then
    printf "Missing arguments.\n${GENERAL_USAGE}" >&2
        exit ${INVALID_USAGE}
    fi
    
    # Parse command options by getopt
    ARGS=$(getopt -o s:m:r:he -l "signaling-artifacts:,media-artifacts:,release:,help,examples" -n "rebase.bash" -- "$@")
    val=${?}

    if [[ ${val} != 0 ]] ; then
        printf "Failed to parse command line parameters by getopt." >&2
        exit ${GETOPT_EXE_ERROR}
    fi
    
    eval set -- "$ARGS"
	
    while true; do
        case "$1" in
			-h|--help)
				printf "${EXTENDED_USAGE}"
				exit 0
				;;
			-e|--examples)
				printf "${EXAMPLES}"
				exit 0
				;;
			-s|--signaling-artifacts)
				SIG_ARTIFACTS_ZIP="${2}"
				shift 2
				;;
			-m|--media-artifacts)
				MEDIA_ARTIFACTS_ZIP="${2}"
				shift 2
				;;
			-r|--release)
				SBC_RELEASE="${2}"
				shift 2
				;;	
			--)
				shift;
				break;
				;;
			*)
				printf "ERROR: ${this} Invalid argument. See usage:\n${GENERAL_USAGE}" >&2
				exit ${INVALID_USAGE}
				;;
	esac
	done
    
    return ${val}
}

function signaling_actifacts_process
{
    typeset val=0
    
    ${MKDIR} -p ${SIG_UNZIP_TARGET_PATH}
    
    ${UNZIP} -d ${SIG_UNZIP_TARGET_PATH} ${SIG_ARTIFACTS_ZIP}
    
    return ${val}
}

function media_artifacts_process
{
    typeset val=0
    
    ${MKDIR} -p ${MEDIA_UNZIP_TARGET_PATH}
    
    ${UNZIP} -d ${MEDIA_UNZIP_TARGET_PATH} ${MEDIA_ARTIFACTS_ZIP}
    
    return ${val}     
}

function post_process
{
    # Once the assessment is finished, delete all artifacts
    ${RM} -rf ${SIG_UNZIP_TARGET_PATH}
    
    ${RM} -rf ${MEDIA_UNZIP_TARGET_PATH}
}
#############################################################
#    			Main Function
#############################################################
parse_opts "$@"

typeset ret_val=-1

signaling_actifacts_process
ret_val=${?}

media_artifacts_process
ret_val=${?}

network_validation
ret_val=${?}

domain_validation 

interconnection_validation

sbc_feature_validation

timezone_ntp_validation

openstack_cloud_validation

post_process

exit ${ret_val}
