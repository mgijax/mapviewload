#!/usr/local/bin/python
#
#  mapviewload.py
###########################################################################
#
#  Purpose:
#
#      Use the mapview input file ($MAPVIEW_FILE), an NCBI file
#      that contains human coordinates, to generate a file for the 
#      coordinate load product (coordload).
#
#      input: $MAPVIEW_FILE, NCBI file
#      output: $INPUT_PRECOORD_FILE, $INPUT_COORD_FILE, input file for coordindate load (coordload)
#
#  Usage:
#
#      mapviewload.py
#
#  Env Vars:
#
#      The following environment variables are set by the configuration
#      file that is sourced by the wrapper script (mapviewload.config):
#
#          MAPVIEW_FILE
#	   INPUT_PRECOORD_FILE
#	   INPUT_COORD_FILE
#	   MAPVIEWQC_NomenMisMatch
#	   MAPVIEWQC_ChrMisMatch
#	   MAPVIEWQC_MultipleCoords
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
#      - Pre-Human Coordinate file ($INPUT_COORD_FILE)
#	 This file is identifcal to the "final" file, except this file contains duplicates.
#	 The duplciates are reported in MAPVIEWQC_MultipleCoords.
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
# 	 if NCBI symbol do not match MGD symbol
#
#      - Chromosome Mismatch report
# 	 if NCBI chromosome do not match MGD chromosome
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
# INPUT_PRECOORD_FILE
precoordFile = None
coordFile = None

# MAPVIEWQC_NomenMisMatch
nomenMisMatchFile = None

# MAPVIEWQC_ChrMisMatch
chrMisMatchFile = None

# MAPVIEWQC_MultipleCoords
mulipleCoordsFile = None

# file pointers
fpMapview = None
fpCoord = None
fpNomenMisMatch = None
fpChrMisMatch = None
fpMultipleCoords = None

# lookup of MGI Human data (EntrezGene id, symbol, chromsome)
mgiLookup = {}

# lookup of EG ids
egLookup = []

#
# Purpose: Initialization
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def initialize():
    global mapviewFile, precoordFile, coordFile, nomenMisMatchFile, chrMisMatchFile, multipleCoordsFile
    global fpMapview, fpPreCoord, fpCoord, fpNomenMisMatch, fpChrMisMatch, fpMultipleCoords

    mapviewFile = os.getenv('MAPVIEW_FILE')
    precoordFile = os.getenv('INPUT_PRECOORD_FILE')
    coordFile = os.getenv('INPUT_COORD_FILE')
    nomenMisMatchFile = os.getenv('MAPVIEWQC_NomenMisMatch')
    chrMisMatchFile = os.getenv('MAPVIEWQC_ChrMisMatch')
    multipleCoordsFile = os.getenv('MAPVIEWQC_MultipleCoords')

    rc = 0

    #
    # Make sure the environment variables are set.
    #
    if not mapviewFile:
        print 'Environment variable not set: MAPVIEW_FILE'
        rc = 1

    if not precoordFile:
        print 'Environment variable not set: INPUT_PRECOORD_FILE'
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

    if not multipleCoordsFile:
        print 'Environment variable not set: MAPVIEWQC_MultipleCoords'
        rc = 1

    #
    # Initialize file pointers.
    #
    fpMapview = None
    fpPreCoord = None
    fpCoord = None
    fpNomenMisMatch = None
    fpChrMisMatch = None
    fpMultipleCoords = None

    return rc


#
# Purpose: Open files.
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def openFiles():
    global fpMapview, fpPreCoord, fpCoord, fpNomenMisMatch, fpChrMisMatch, fpMultipleCoords
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
    # Open the pre-coordinate file.
    #
    try:
        fpPreCoord = open(precoordFile, 'w')
    except:
        print 'Cannot open file: ' + precoordFile
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
    # Open the multiple coordinates file.
    #
    try:
        fpMultipleCoords = open(multipleCoordsFile, 'w')
    except:
        print 'Cannot open file: ' + multipleCoordsFile
        return 1

    #
    # write headers for qc reports
    #

    fpNomenMisMatch.write('''
Report of human genes with coordinates not loaded because
nomenclature in the coordinates source file (seq_gene.md from
NCBI, generated when the genome build was initially released) 
has become out-of-sync with nomenclature in the Entrez Gene 
load (regenerated on a regular basis.)
    ''')


    fpNomenMisMatch.write("\n\nHuman Gene Coordinates Load - Nomenclature Mismatches\n\n")
    fpNomenMisMatch.write("column 1 : Gene ID from NCBI\n")
    fpNomenMisMatch.write("column 2 : Symbol in Coordinates file\n")
    fpNomenMisMatch.write("column 3 : Symbol in MGI's current data\n\n")

    fpChrMisMatch.write('''
Report of human genes with coordinates not loaded because
chromosome in the coordinates source file (seq_gene.md from
NCBI, generated when the genome build was initially released)
has become out-of-sync with chromosome in the Entrez Gene
load (regenerated on a regular basis.)
    ''')

    fpChrMisMatch.write("\n\n\tHuman Gene Coordinates Load - Chromosome Mismatches\n\n")
    fpChrMisMatch.write("column 1 : Gene ID from NCBI\n")
    fpChrMisMatch.write("column 2 : Chromosome in Coordinates file\n")
    fpChrMisMatch.write("column 3 : Chromosome in MGI's current data\n\n")

    fpMultipleCoords.write('''
Report of human genes with coordinates not loaded because
multiple sets of the coordinates appear in the source file 
(seq_gene.md from NCBI, generated when the genome build was 
initially released).
    ''')

    fpMultipleCoords.write("\n\n\tHuman Gene Coordinates Load - Multiple Coordinates\n\n")
    fpMultipleCoords.write("column 1 : Gene ID from NCBI\n")
    fpMultipleCoords.write("column 2 : Chromosome in Coordinates file\n")
    fpMultipleCoords.write("column 3 : Start Coordinate in Coordinates file\n")
    fpMultipleCoords.write("column 4 : End Coordinate in Coordinates file\n")
    fpMultipleCoords.write("column 5 : Strand in the Coordinates file\n\n")

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

    if fpPreCoord:
        fpPreCoord.close()

    if fpCoord:
        fpCoord.close()

    if fpNomenMisMatch:
        fpNomenMisMatch.close()

    if fpChrMisMatch:
        fpChrMisMatch.close()

    if fpMultipleCoords:
        fpMultipleCoords.close()

    return 0


#
# Purpose: Use mapview file to generate coordinate file.
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def getCoordinates():
    global fpPreCoord, egLookup

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

	# TR6519 - let's be build/patch neutral, skip if not 'GRCh*Primary Assembly'
	if not(string.find(group_label, 'GRCh') >= 0 and \
		string.find(group_label, 'Primary Assembly') >= 0):
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

	# check if NCBI symbol do not match the MGD symbol
	# allow the load, but report the difference
	mgiSymbol = mgiLookup[feature_id]['symbol']
	if mgiSymbol != feature_name:
	    fpNomenMisMatch.write(feature_id + '\t' + feature_name + '\t' + mgiSymbol + '\n')

	fpPreCoord.write(feature_id + '\t')
	fpPreCoord.write(chromosome + '\t')
	fpPreCoord.write(chr_start + '\t')
	fpPreCoord.write(chr_stop + '\t')
	fpPreCoord.write(chr_orient + '\n')

	if feature_id in egLookup:
	    egLookup.remove(feature_id)
        else:
	    egLookup.append(feature_id)

    fpPreCoord.close()

    #
    # open pre-coordinate file and check for duplicates
    #

    #
    # Open the pre-coordinate file.
    #
    try:
        fpPreCoord = open(precoordFile, 'r')
    except:
        print 'Cannot open file: ' + precoordFile
        return 1

    for line in fpPreCoord.readlines():

	tokens = string.split(line[:-1], '\t')

	feature_id = tokens[0]
	chromosome = tokens[1]
	chr_start = tokens[2]
	chr_stop = tokens[3]
	chr_orient = tokens[4]

	if feature_id not in egLookup:
	    fpMultipleCoords.write(feature_id + '\t' +  \
				   chromosome + '\t' +  \
				   chr_start + '\t' +  \
				   chr_stop + '\t' +  \
				   chr_orient + '\n')
	    continue;

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

