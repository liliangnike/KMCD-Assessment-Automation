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
INVALID_USAGE=3
REPO_DIR_NOT_EXIST=4
HG_PURGE_FAIL=5
HG_UPDATE_CLEAN_FAIL=6
HG_REBASE_FAIL=7
INVALID_INPUT_OPTION=8
UNRESOLVED_CONFLICT=9

# Global Variables
typeset ms_par_changeset=""

# Global commands set
typeset PURGE="/usr/local/bin/hg purge"


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
    ARGS=$(getopt -o c:m:l:t:f:he -l "central_ms_repo:,local_ms_repo:,central_fdt_repo:,local_fdt_repo:,fr:,help,examples" -n "rebase.bash" -- "$@")
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
				central_ms_repo="${2}"
				shift 2
				;;
			-m|--media-artifacts)
				local_ms_repo="${2}"
				shift 2
				;;
			-r|--release)
				central_fdt_repo="${2}"
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

exit ${ret_val}
