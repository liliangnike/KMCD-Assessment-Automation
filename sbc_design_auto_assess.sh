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
typeset ms_par_changeset_debug=""
typeset fdt_par_changeset_debug=""

typeset central_ms_repo=""
typeset local_ms_repo=""
typeset central_fdt_repo=""
typeset local_fdt_repo=""

typeset FR_to_rebase=""

# Global commands set
typeset PURGE="/usr/local/bin/hg purge"
typeset UPDATE_CLEAN="/usr/local/bin/hg update --clean"
typeset PULL_UPDATE="/usr/local/bin/hg pull -u"
typeset HG_PAR="/usr/local/bin/hg par"
typeset HG_PAR_DEBUG="/usr/local/bin/hg par --debug"
typeset HG_CI="/usr/local/bin/hg ci"
typeset HG_OUTGOING="/usr/local/bin/hg outgoing"
typeset HG_PUSH="/usr/local/bin/hg push"

typeset HG_REBASE="/home/buildmgr/bin/HG_brebase.sh"
typeset POST_REVIEW="/usr/bin/post-review"

typeset SHIP_REVIEW="~/bin/ship"


GENERAL_USAGE="USAGE:
${THIS} < --help | --examples >
  or
${THIS} --central_ms_repo <central MS repo> --local_ms_repo <local MS repo>\n\
 \n--central_fdt_repo <central FDT repo> --local_fdt_repo <local FDT repo> --fr <FR used to do rebase>\n"

EXTENDED_USAGE="${GENERAL_USAGE}

Where,

--help - shows extended usage

--examples - shows some example usages.

--central_ms_repo - MS repo directory in central code repository server

--local_ms_repo - MS repo directory of local user

--central_fdt_repo - FDT repo directory in central code repository server

--local_fdt_repo - FDT repo directory of local user

--fr - FR number used to do rebase

"

EXAMPLES="
EXAMPLES:

${THIS} --central_ms_repo ssh://hg@135.251.206.233/HD_R5601 --local_ms_repo /repo/leonll/HD_R5601\
\n --central_fdt_repo ssh://hg@135.251.206.233/HD_R5601_FDT1480 --local_fdt_repo /repo/leonll/HD_R5601_FDT1480 --fr ALU02375967

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
			-r|--sbc-release)
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
