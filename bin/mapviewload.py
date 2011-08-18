#!/usr/local/bin/python
#
#  mapviewload.py
###########################################################################
#
#  Purpose:
#
#      This script will use the records in the mapview input file to create
#      output files that contain:
#
#  Usage:
#
#      mapviewload.py
#
#  Env Vars:
#
#      The following environment variables are set by the configuration
#      file that is sourced by the wrapper script:
#
#          MAPVIEW_FILE
#	   INPUT_COORD_FILE
#	   MAPVIEWQC_NomenMisMatch
#	   MAPVIEWQC_ChrMisMatch
#
#  Inputs:
#
#      - mapview file ($MAPVIEW_FILE)
#	 It has the following tab-delimited fields:
#	 1) tax_id
#	 2) chromosome
#	 3) chr_start
#	 4) chr_stop
#	 5) chr_orient (strand)
#	 10) feature_name
#	 11) feature_id (GeneID:xxxx ==> EntrezGene id)
#	 12) feature_type = "GENE"
#	 13) group_label = "GRChxxxx-Primary Assembly"
#
#  Outputs:
#
#      - Human Coordinate file ($INPUT_COORD_FILE)
#        It has the following tab-delimited fields:
#        1) ID (e.g. human entrezgene id)
#        2) Chromosome
#        3) Start Coordinate
#        4) End Coordinate
#        5) Strand (+ or - or null)
#
#      - Nomenclature Mismatch report
#
#      - Chromosome Mismatch report
#
#  Exit Codes:
#
#      0:  Successful completion
#      1:  An exception occurred
#
#  Assumes:  Nothing
#
#  Implementation:
#
#      This script will perform following steps:
#
#      1) Initialize variables.
#      2) Open files.
#      3) Write each EntrezGene id to the coordinate file
#	  if feature_id = EntrezGene id
#	    if chromosome == MGD chromosome:  load else send to mismatch report
#	    if feature_name == MGD symbol: load and send to mismatch report
#      4) Close files.
#
#  Notes:  None
#
###########################################################################

import sys 
import os
import string
import db

# MAPVIEW_FILE
mapviewFile = None

# INPUT_COORD_FILE
coordFile = None

# MAPVIEWQC_NomenMisMatch
nomenMisMatchFile = None

# MAPVIEWQC_ChrMisMatch
chrMisMatchFile = None

# file pointers
fpMapview = None
fpCoord = None
fpNomenMisMatch = None
fpChrMisMatch = None

# lookup of MGI Human data (EntrezGene id, symbol, chromsome)
mgiLookup = {}

#
# Purpose: Initialization
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def initialize():
    global mapviewFile, coordFile, nomenMisMatchFile, chrMisMatchFile
    global fpMapview, fpCoord, fpNomenMisMatch, fpChrMisMatch

    mapviewFile = os.getenv('MAPVIEW_FILE')
    coordFile = os.getenv('INPUT_COORD_FILE')
    nomenMisMatchFile = os.getenv('MAPVIEWQC_NomenMisMatch')
    chrMisMatchFile = os.getenv('MAPVIEWQC_ChrMisMatch')

    rc = 0

    #
    # Make sure the environment variables are set.
    #
    if not mapviewFile:
        print 'Environment variable not set: MAPVIEW_FILE'
        rc = 1

    if not coordFile:
        print 'Environment variable not set: INPUT_COORD_FILE'
        rc = 1

    if not nomenMisMatchFile:
        print 'Environment variable not set: MAPVIEWQC_NomenMisMatch'
        rc = 1

    if not chrMisMatchFile:
        print 'Environment variable not set: MAPVIEWQC_ChrMisMatch'
        rc = 1

    #
    # Initialize file pointers.
    #
    fpMapview = None
    fpCoord = None
    fpNomenMisMatch = None
    fpChrMisMatch = None

    return rc


#
# Purpose: Open files.
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def openFiles():
    global fpMapview, fpCoord, fpNomenMisMatch, fpChrMisMatch
    global mgiLookup

    #
    # Open the mapview file.
    #
    try:
        fpMapview = open(mapviewFile, 'r')
    except:
        print 'Cannot open file: ' + mapviewFile
        return 1

    #
    # Open the coordinate file.
    #
    try:
        fpCoord = open(coordFile, 'w')
    except:
        print 'Cannot open file: ' + coordFile
        return 1

    #
    # Open the nomenclature mismatch file.
    #
    try:
        fpNomenMisMatch = open(nomenMisMatchFile, 'w')
    except:
        print 'Cannot open file: ' + nomenMisMatchFile
        return 1

    #
    # Open the chromosome mismatch file.
    #
    try:
        fpChrMisMatch = open(chrMisMatchFile, 'w')
    except:
        print 'Cannot open file: ' + chrMisMatchFile
        return 1

    #
    # Select all human markers that contain EntrezGene ids
    # and are statused as 'official'
    #
    results = db.sql('''
	select a.accID, m.symbol, m.chromosome
	from MRK_Marker m, ACC_Accession a
	where m._Organism_key = 2
	and m._Marker_Status_key = 1
	and m._Marker_key = a._Object_key
	and a._MGIType_key = 2
	and a._LogicalDB_key = 55
	''', 'auto')

    # store this set in the mgiLookup
    for r in results:
	egID = r['accID']
	mgiLookup[egID] = r

    return 0


#
# Purpose: Close files.
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def closeFiles():

    if fpMapview:
        fpMapview.close()

    if fpCoord:
        fpCoord.close()

    if fpNomenMisMatch:
        fpNomenMisMatch.close()

    if fpChrMisMatch:
        fpChrMisMatch.close()

    return 0


#
# Purpose: Use mapview file to generate coordinate file.
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def getCoordinates():

    #
    # Process each record returned from mapview
    #
    for line in fpMapview.readlines():

        #
        # Get the IDs from the record.
        #
	tokens = string.split(line[:-1], '\t')

        taxID = tokens[0]
	chromosome = tokens[1]
	chr_start = tokens[2]
	chr_stop = tokens[3]
	chr_orient = tokens[4]
	feature_name = tokens[9]
	feature_id = tokens[10]
	feature_type = tokens[11]
	group_label = tokens[12]

	# skip if feature_type does not = 'GENE'
	if string.find(feature_type, 'GENE') < 0:
	    continue

	# skip if group_label does not contain 'GRCh37.p2-Primary Assembly'
	if string.find(group_label, 'GRCh37.p2-Primary Assembly') < 0:
	    continue

	# skip if feature_id (EntrezGene id) does not exist in MGI 
	feature_id = string.replace(feature_id, 'GeneID:', '')
	if not mgiLookup.has_key(feature_id):
	    continue

	# skip if chromosome values do not match
	mgiChromosome = mgiLookup[feature_id]['chromosome']
	if mgiChromosome != chromosome:
	    fpChrMisMatch.write(feature_id + '\t' + chromosome + '\t' + mgiChromosome + '\n')
	    continue

	# check if symbol values do not match
	# allow the load, but report the difference
	mgiSymbol = mgiLookup[feature_id]['symbol']
	if mgiSymbol != feature_name:
	    fpNomenMisMatch.write(feature_id + '\t' + feature_name + '\t' + mgiSymbol + '\n')

	fpCoord.write(feature_id + '\t')
	fpCoord.write(chromosome + '\t')
	fpCoord.write(chr_start + '\t')
	fpCoord.write(chr_stop + '\t')
	fpCoord.write(chr_orient + '\n')

    return 0


#
#  MAIN
#

if initialize() != 0:
    sys.exit(1)

if openFiles() != 0:
    sys.exit(1)

if getCoordinates() != 0:
    closeFiles()
    sys.exit(1)

closeFiles()
sys.exit(0)

