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
			-c|--central_ms_repo)
				central_ms_repo="${2}"
				shift 2
				;;
			-m|--local_ms_repo)
				local_ms_repo="${2}"
				shift 2
				;;
			-l|--central_fdt_repo)
				central_fdt_repo="${2}"
				shift 2
				;;
			-t|--local_fdt_repo)
				local_fdt_repo="${2}"
				shift 2
				;;	
                        -f|--fr)
                                FR_to_rebase="${2}"
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

function get_ms_par_changeset
{
    typeset -i ret_val=0
    typeset par_cmd_result=""
    typeset par_debug_cmd_result=""

    if [[ ! -d "${local_ms_repo}" ]]; then
        printf "File ${local_ms_repo} does not exist." >&2 
        ret_val=${REPO_DIR_NOT_EXIST}
    else
        clean_to_sync_repo ${local_ms_repo}

        par_cmd_result=$(${HG_PAR})
        printf "${par_cmd_result}\n\n"
        ms_par_changeset=$(get_par_changeset "${par_cmd_result}")
        ret_val=${?}

        par_debug_cmd_result=$(${HG_PAR_DEBUG})
        printf "${par_debug_cmd_result}\n"
        ms_par_changeset_debug=$(get_par_changeset "${par_debug_cmd_result}")
        ret_val=${?}
    fi
    
    return ${ret_val}
}

function clean_to_sync_repo
{
    typeset -i ret_val=0
    typeset repo=${1}

    if [[ ! -d "${repo}" ]]; then
        printf "Repo directory ${repo} does not exist." >&2
        ret_val=${REPO_DIR_NOT_EXIST}
    else 
        cd ${repo}
        printf "\nEnter into ${repo} to clean...\n\n"
		
        ${PURGE}
        ret_val=${?}
        if (( ${ret_val} != 0 )); then
            printf "Failed to execute command ${PURGE}.\n" >&2
            exit ${HG_PURGE_FAIL}
        fi
        printf "${repo} has been purged.\n\n"
		
        ${UPDATE_CLEAN}
        ret_val=${?}
        if (( ${ret_val} != 0 )); then
            printf "Failed to execute command ${UPDATE_CLEAN}.\n" >&2
            exit ${HG_UPDATE_CLEAN_FAIL}
        fi
        printf "${repo} has been updated and cleaned\n\n"
		
        # If no code update, "hg pull -u" returns 1.
        ${PULL_UPDATE}

    fi 

    return ${ret_val}
}

function get_par_changeset
{
    typeset -i ret_val=0
    typeset hg_par_cmd_result=${1}
    typeset par_changeset=""

    par_changeset=$(echo ${hg_par_cmd_result} | cut -d ":" -f 3 | cut -d " " -f 1)
    ret_val=${?}

    printf "${par_changeset}"

    return ${ret_val}
}

function get_fdt_par_changeset
{
    typeset -i ret_val=0
    typeset par_debug_cmd_result=""

    if [[ ! -d "${local_fdt_repo}" ]]; then
        printf "File ${local_fdt_repo} does not exist." >&2
        ret_val=${REPO_DIR_NOT_EXIST}
    else
        clean_to_sync_repo ${local_fdt_repo}

        par_debug_cmd_result=$(${HG_PAR_DEBUG})
        printf "${par_debug_cmd_result}\n"
        fdt_par_changeset_debug=$(get_par_changeset "${par_debug_cmd_result}")
        ret_val=${?}
    fi

    return ${ret_val}
}

function do_rebase
{
    typeset -i ret_val=0
    typeset unresolve_txt="${local_fdt_repo}/unresolve.txt"
	
    ${HG_REBASE} -f ${central_ms_repo} ${ms_par_changeset_debug} -t ${central_fdt_repo} ${fdt_par_changeset_debug}

    # check unresolve.txt under FDT repo
    if  [[ -f "${unresolve_txt}" ]]; then
        wait_user_to_resolve_confict ${unresolve_txt}
        exit ${UNRESOLVED_CONFLICT}
    fi
	
    return ${ret_val}
}

function wait_user_to_resolve_confict
{
    # to do later
    print ${1}
}

function check_in_fdt_changes
{
    cd ${local_fdt_repo}
    ${HG_CI} -u ${USER} -m "FR ${FR_to_rebase}: rebase with MS changset ${ms_par_changeset}"
    # notice below case
    # [leonll@AONT24 HD_R5701_FDT1480]$ hg ci -u leonll -m 'FR ALU02375967: rebase with MS changset 27fe2e5aa327'
    # nothing changed

}

function send_post_review
{
    typeset outgoing_changsets=""
    typeset post_review_cs=""

    cd ${local_fdt_repo}
    outgoing_changsets=$(${HG_OUTGOING})
    post_review_cs=$(echo "${outgoing_changsets}" | grep "changeset:" | cut -d ':' -f 3 | tail -n 1)

    printf "Changeset for sending code review is ${post_review_cs}.\n"
    ${POST_REVIEW} --revision-range=${post_review_cs} --target-people=${USER}

} 

function is_post_review_closed
{
    typeset is_shipped=""
    printf "Type 'y' to push changes; type 'n' to push the changes later:"
    read is_shipped 
    if [[ ${is_shipped} == ['y''Y'] ]]; then
	cd ${local_fdt_repo}
        ${HG_PUSH}       
    elif [[ ${is_shipped} == ['n''N'] ]]; then
	printf "User selected not to push changes. Please remember to push the rebased changesets later."	
    else
	printf "Invalid input, exit rebase. Please remember to push the rebased changesets later."
        exit ${INVALID_INPUT_OPTION}
    fi

}

#############################################################
#    			Main Function
#############################################################
parse_opts "$@"

typeset ret_val=-1

get_ms_par_changeset
ret_val=${?}

get_fdt_par_changeset
ret_val=${?}

do_rebase
ret_val=${?}

check_in_fdt_changes 

send_post_review

is_post_review_closed

#do_pullme


exit ${ret_val}
