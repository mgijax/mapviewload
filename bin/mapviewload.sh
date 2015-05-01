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
if [ $# -ne 1 ]
then
    echo ${Usage} | tee -a ${LOG}
    exit 1
fi

LOAD_CACHE=$1

#
# verify & source the load configuration file
#

CONFIG_LOAD=`pwd`/mapviewload.config

if [ ! -r ${CONFIG_LOAD} ]
then
    echo "Cannot read configuration file: ${CONFIG_LOAD}"
    exit 1
fi

. ${CONFIG_LOAD}

#
# verify the coordinate load configuration file
#

CONFIG_COORD=`pwd`/coordload.config

if [ ! -r ${CONFIG_COORD} ]
then
    echo "Cannot read configuration file: ${CONFIG_COORD}"
    exit 1
fi

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
# There should be a "lastrun" file in the input directory that was created
# the last time the load was run for this input file. If this file exists
# and is more recent than the input file, the load does not need to be run.
#
LASTRUN_FILE=${INPUTDIR}/lastrun
if [ -f ${LASTRUN_FILE} ]
then
    if test ${LASTRUN_FILE} -nt ${MAPVIEWDIR}/${MAPVIEWGZ}
    then

        echo "Input file has not been updated - skipping load" | tee -a ${LOG_PROC}
        # set STAT for shutdown
        STAT=0
        echo 'shutting down'
        shutDown
        exit 0
    fi
fi

#
# rm files and dirs from OUTPUTDIR
#

cleanDir ${OUTPUTDIR}

# remove old unzipped file
rm -rf ${MAPFILE_NAME}

# copy new file from /data/downloads and unzip
cd ${INPUTDIR}
cp -p ${MAPVIEWDIR}/${MAPVIEWGZ} ${INPUTDIR}

# process the input
/usr/local/bin/gunzip -f ${MAPVIEWGZ} >> ${LOG_DIAG}

# get the build number from the input file
# we need to pass this to the java system properties when calling the coordload
build=`cat seq_gene.md | cut -f 13 | sort | uniq | cut -d"-" -f1 | grep "GRCh" |
 sort | uniq`

echo "build: ${build}"

#
# process the input file
#
echo "" >> ${LOG_DIAG} 
echo "`date`" >> ${LOG_DIAG} 
echo "Processing input file ${MAPFILE_NAME}" | tee -a ${LOG_DIAG}
${MAPVIEWLOAD}/bin/mapviewload.py | tee -a ${LOG_DIAG} ${LOG_PROC}
STAT=$?
checkStatus ${STAT} "${MAPVIEWLOAD}/bin/mapviewload.py"

#
# run the coordinate load
#
. ${CONFIG_COORD}
echo "" >> ${LOG_DIAG}
echo "`date`" >> ${LOG_DIAG}
echo "Running human coordinate load" | tee -a ${LOG_DIAG} ${LOG_PROC}
${JAVA} ${JAVARUNTIMEOPTS} -classpath ${CLASSPATH} \
    -DCONFIG=${CONFIG_MASTER},${CONFIG_COORD} \
    -DCOORD_VERSION="${build}" \
    -DJOBKEY=${JOBKEY} ${DLA_START}

STAT=$?
checkStatus ${STAT} "human coordinate java load"

#
# now source the mapview config to close logs
#
. ${CONFIG_LOAD}

#
# Load the marker location cache?
#
if [ ${LOAD_CACHE} = "true" ]
then
    echo "" >> ${LOG_DIAG}
    echo "`date`" >> ${LOG_DIAG}
    echo "Running marker location cacheload"| tee -a ${LOG_DIAG}
    ${LOCATIONCACHE_SH} >> ${LOG_DIAG}
    STAT=$?
    checkStatus ${STAT} "${LOCATIONCACHE_SH}"
fi

#
# Touch the "lastrun" file to note when the load was run.
#
if [ ${STAT} = 0 ]
then
    touch ${LASTRUN_FILE}
fi

#
# Perform post-load tasks.
#
shutDown

exit 0
