#!/bin/sh
#
# mapview Load Jobstream Wrapper
############################################################################
#
# Purpose:
#
# 	Parse the MGI-generated file human_coord.txt 
#	into these output files:
#		1.  coordinate loader file
#
#	We only load one coordinate per Marker.
#
#       (mapviewload.py)
#
#	Load the output files into the database.
#		1. invoke coordinate loader
#		2. update MRK_Location_Cache table
#
Usage="mapviewload.sh true|false"
#       true if reloading MRK_Location_Cache
# History
#
# 08/18/2011	lec
#	- TR 10805
#
###########################################################################

#
#  Set up a log file for the shell script in case there is an error
#  during configuration and initialization.
#

cd `dirname $0`/..
LOG=`pwd`/`basename $0`.log
rm -rf ${LOG}
touch ${LOG}

#
#  Verify the argument(s) to the shell script.
#
#if [ $# -ne 1 ]
#then
#    echo ${Usage} | tee -a ${LOG}
#    exit 1
#fi

LOAD_CACHE=$1

CONFIG_LOAD=`pwd`/mapviewload.config

#
# verify & source the miRBASE load configuration file
#

if [ ! -r ${CONFIG_LOAD} ]
then
    echo "Cannot read configuration file: ${CONFIG_LOAD}"
    exit 1
fi

. ${CONFIG_LOAD}

#
#  Source the DLA library functions.
#

if [ "${DLAJOBSTREAMFUNC}" != "" ]
then
    if [ -r ${DLAJOBSTREAMFUNC} ]
    then
        . ${DLAJOBSTREAMFUNC}
    else
        echo "Cannot source DLA functions script: ${DLAJOBSTREAMFUNC}" | tee -a ${LOG}
        exit 1
    fi
else
    echo "Environment variable DLAJOBSTREAMFUNC has not been defined." | tee -a ${LOG}
    exit 1
fi

#
# check that MAPVIEWGZ has been set and exists
#
if [ "${MAPVIEWDIR}/${MAPVIEWGZ}" = "" ]
then
     # set STAT for endJobStream.py called from postload in shutDown
    STAT=1
    checkStatus ${STAT} "MAPVIEWDIR/MAPVIEWGZ not defined"
fi

if [ ! -r ${MAPVIEWDIR}/${MAPVIEWGZ} ]
then
    # set STAT for endJobStream.py called from postload in shutDown
    STAT=1
    checkStatus ${STAT} "MAPVIEW file: ${MAPVIEWDIR}/${MAPVIEWGZ} does not exist"
fi

##################################################################
##################################################################
#
# main
#
##################################################################
##################################################################

#
# createArchive including OUTPUTDIR, startLog, getConfigEnv, get job key
#

preload ${OUTPUTDIR}

#
# rm files and dirs from OUTPUTDIR
#

cleanDir ${OUTPUTDIR} 

# remove old files
#rm -rf ${MAPFILE_NAME}

# copy new file from /data/downloads and unzip
#cd ${INPUTDIR}
#cp ${MAPVIEWDIR}/${MAPVIEWGZ} ${INPUTDIR}
#/usr/local/bin/gunzip -f ${MAPVIEWGZ} >> ${LOG_DIAG}

#
# process the input file
#
#echo "\n`date`" >> ${LOG_DIAG} 
#echo "Processing input file ${MAPFILE_NAME}" | tee -a ${LOG_DIAG}
#${MAPVIEWLOAD}/bin/mapviewload.py | tee -a ${LOG_DIAG} ${LOG_PROC}
#STAT=$?
#checkStatus ${STAT} "${MAPVIEWLOAD}/bin/mapviewload.py"

#
# run the coordinate load
#
echo "\n`date`" >> ${LOG_DIAG}
echo "Running coordinate load" | tee -a ${LOG_DIAG}
${COORDLOADER_SH} ${CONFIG_LOAD} ${COORDLOADCONFIG}  >> ${LOG_DIAG}
STAT=$?
checkStatus ${STAT} "${COORDLOADER_SH}"

#if [ ${LOAD_CACHE} = "true" ]
#then
#    echo "\n`date`" >> ${LOG_DIAG}
#    echo "Running marker location cacheload"| tee -a ${LOG_DIAG}
#    ${LOCATIONCACHE_SH} >> ${LOG_DIAG}
#    STAT=$?
#    checkStatus ${STAT} "${LOCATIONCACHE_SH}"
#fi

#
# Perform post-load tasks.
#
shutDown

exit 0
