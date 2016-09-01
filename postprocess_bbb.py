#! /usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
# Copyright (c) 2012-6 Bryce Adelstein Lelbach aka wash <brycelelbach@gmail.com>
#
# Distributed under the Boost Software License, Version 1.0. (See accompanying
# file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
###############################################################################

from math import sqrt
from sys import exit

from optparse import OptionParser

from numpy import std, mean

from os.path import splitext

from re import match as regex_match

op = OptionParser(
    # Usage:  
    usage=("%prog [options] input-data\n"
           "       %prog [options] input-data output-data output-gnuplot-header")
)

op.add_option(
    "-v", "--classify-variable",
    help=("Classify a particular variable (TAG) as a control (CTL), independent "
          "(IND) or dependent (DEP) variable. Overrides the classification "
          "specified in the file. Parameters should be specified as TAG=TYPE, "
          "where TAG is a variable tag, and TYPE is either CTL, IND or DEP."),
    action="append", type="string", dest="variable_classifications",
    metavar="TAG=TYPE"
)

op.add_option(
    "-i", "--filter-in",
    help=("Only include records for which the specified variable (TAG) is "
          "equal to the given value (VALUE). Applied consecutively before "
          "--filter-out options."),
    action="append", type="string", dest="inclusive_filters",
    metavar="TAG=VALUE"
)

op.add_option(
    "-o", "--filter-out",
    help=("Only include records for which the specified variable (TAG) is not "
          "equal the given value (VALUE). Applied consecutively before "
          "--filter-out options."),
    action="append", type="string", dest="exclusive_filters",
    metavar="TAG=VALUE"
)

(options, args) = op.parse_args()

if len(args) != 1 and len(args) != 3:
    op.print_help()
    exit(1)

input_data = None
output_data = None
output_header = None

if   len(args) == 1:
    prefix = splitext(args[0])[0]
    input_data = open(args[0] , 'r')
    output_data = open("post_" + prefix + ".bbb", 'w')
    output_header = open("post_" + prefix + ".gpi", 'w')
elif len(args) == 3:
    input_data = open(args[0], 'r')
    output_data = open(args[1], 'w')
    output_header = open(args[2], 'w')
else:
    assert len(args) != 1 and len(args) != 3 

CTL = 1 # Control variables, used to distinguish datasets
IND = 2 # Independent variables
DEP = 3 # Dependent variables (averaged and stdev'd)
 
def vtype_to_str(vt):
    if   CTL == vt: return "CTL"
    elif IND == vt: return "IND"
    elif DEP == vt: return "DEP"

    else:
        assert CTL == vt or IND == vt or DEP == vt
        return None

def str_to_vtype(s):
    if   "CTL" == s: return CTL
    elif "IND" == s: return IND
    elif "DEP" == s: return DEP

    else:
        assert "CTL" == s or "IND" == s or "DEP" == s 
        return None

def try_int_or_float(x):
    try:
        try:
            return int(x)
        except ValueError:
            return float(x)
    except ValueError:
        return x

# Returns (tag, vtype) where tag is a string and vtype is an integer
def parse_variable_classification(vc):
    match = regex_match(r'([a-zA-Z0-9_]+)=((CTL)|(IND)|(DEP))', vc)

    if match is None:
        print "ERROR: Variable classification (-v) '"+vc+"' is invalid, the "+\
              "format is TAG=TYPE, where TAG is a variable tag and TYPE is "+\
              "either CTL, IND or DEP."
        exit(1)

    return (match.group(1), str_to_vtype(match.group(2)))

# Returns (tag, value) where tag is a string and vtype is an integer
def parse_filter(fi):
    match = regex_match(r'([a-zA-Z0-9_]+)=(.+)', fi)

    if match is None:
        print "ERROR: Filter '"+fi+"' is invalid, the format is TAG=VALUE, "+\
              "where TAG is a variable tag and VALUE is a valid value for "+\
              "the variable."
        exit(1)

    return (match.group(1), try_int_or_float(match.group(2)))

class variable:
    index = -1
    vtype = 0
    tag = ""
    name = ""
    units = ""

    def __init__(self, index, vtype, tag, name, units):
        self.index = index

        try:
            self.vtype = str_to_vtype(vtype)    
        except AssertionError:
            print "ERROR: Variable "+str((index, vtype, tag, name, units))+\
                  " has a invalid type, options are 'CTL', 'IND' and 'DEP'."
            exit(1)

        self.tag = tag
        self.name = name
        self.units = units

    def __str__(self):
        return str((str(self.index), vtype_to_str(self.vtype), \
                    self.tag, self.name, self.units))        

class vtype_indices:
    vtype = 0
    indices = ()

    def __init__(self, vtype, legend):
        assert CTL in vtype or IND in vtype or DEP in vtype

        l = []

        for (index, v) in sorted(legend.iteritems()):
            if v.vtype in vtype:
                l.append(index)

        self.vtype = vtype
        self.indices = tuple(l)

    def apply(self, row):
        return tuple(try_int_or_float(row[x]) for x in self.indices)

# Given a collection of equal-length sequences, this algorithm finds the set of
# indices which refer to elements that are NOT equal in each sequence.
def find_distinguishing_variables(datasets):
    assert bool(datasets) # Check for emptiness

    cvars_len = len(datasets[0])

    dist_vars = []

    for cvar in range(0, cvars_len):
        different = False
        last_value = None
        for ds in range(0, len(datasets)-1):
            assert len(datasets[ds])   == cvars_len
            assert len(datasets[ds+1]) == cvars_len

            if datasets[ds][cvar] != datasets[ds+1][cvar]:
                different = True
                break
            else:
                last_value = datasets[ds][cvar]

        if different:
            dist_vars.append(cvar)

    return dist_vars

###############################################################################
# Parse the file

master = {}

legend = {}

tags_to_indices = {}

inclusive_filters = []
exclusive_filters = []

cvars  = None # CTLs
civars = None # CTLs and INDs
dvars  = None # DEPs

legend_open = True
legend_index = 0

try:
    while True:
        line = input_data.next()

        line = line.strip()

        #######################################################################
        # Parse the legend

        # Look for the legend 
        if '#' == line[0]:
            if '#' == line[1]:
                # Chop off the ##
                line = line[2:]

                if not legend_open:
                    print "ERROR: Variable declarations must come before any "+\
                          "data."
                    exit(1)

                row = line.split(':')

                if 4 != len(row):
                    print "ERROR: Variable declaration '"+line+"' "+\
                          "has "+str(len(row))+" fields instead of 4."
                    exit(1)

                v = variable(legend_index, *(x.strip() for x in row)) 

                if v.tag in tags_to_indices:
                    print "ERROR: Variable declaration '"+line+"' "+\
                          "is a duplicate."
                    exit(1)

                tags_to_indices[v.tag] = v.index

                legend[v.index] = v                 

                legend_index = legend_index + 1
            else:
                print >> output_data, line, 
            continue

        # Look for blank lines
        if line == "\n":
            continue

        #######################################################################
        # Close the legend, create indices, parse variable classifications and
        # filters

        # Line isn't a comment or a blank, so we've reached the data. We need
        # to close the legend and create the indices. 
        if legend_open:
            legend_open = False

            ###################################################################
            # Parse variable classifications

            if options.variable_classifications is not None:
                for vc in options.variable_classifications:
                    (tag, vtype) = parse_variable_classification(vc)

                    if tag not in tags_to_indices:
                        print "ERROR: Tag '"+tag+"' from variable "+\
                              "classification (-v) '"+vc+"' not found in "+\
                              "input file."
                        exit(1)

                    legend[tags_to_indices[tag]].vtype = vtype

            ###################################################################
            # Parse filters 

            if options.inclusive_filters is not None:
                for fi in options.inclusive_filters:
                    (tag, value) = parse_filter(fi)

                    if tag not in tags_to_indices:
                        print "ERROR: Tag '"+tag+"' from inclusive filter "+\
                              "(-i) '"+fi+"' not found in input file."
                        exit(1)

                    inclusive_filters.append((tag, value))

            if options.exclusive_filters is not None:
                for fi in options.exclusive_filters:
                    (tag, value) = parse_filter(fi)

                    if tag not in tags_to_indices:
                        print "ERROR: Tag '"+tag+"' from exclusive filter "+\
                              "(-i) '"+fi+"' not found in input file."
                        exit(1)

                    exclusive_filters.append((tag, value))
        
            ###################################################################
            # Create indices

            cvars  = vtype_indices([CTL], legend)
            civars = vtype_indices([CTL, IND], legend)
            dvars  = vtype_indices([DEP], legend)

        #######################################################################
        # Parse data

        row = line.split()

        if len(row) != legend_index:
            print "ERROR: Row '"+line+"' has only "+str(len(row))+" "+\
                  "variables, but the legend has "+str(legend_index)+" "+\
                  "variables."

        #######################################################################
        # Apply filters

        skip_record = False

        for (tag, value) in inclusive_filters:
            if try_int_or_float(row[tags_to_indices[tag]]) != value:
                skip_record = True
                break

        for (tag, value) in exclusive_filters:
            if try_int_or_float(row[tags_to_indices[tag]]) == value:
                skip_record = True
                break

        if skip_record:
            continue

        if not cvars.apply(row) in master:
            master[cvars.apply(row)] = {}

        if not civars.apply(row) in master[cvars.apply(row)]:
            master[cvars.apply(row)][civars.apply(row)] = []

            for (i, var) in sorted(legend.iteritems()):
                v = try_int_or_float(row[i])
                if CTL == var.vtype or IND == var.vtype:
                    master[cvars.apply(row)][civars.apply(row)].append(v)
                else:
                    master[cvars.apply(row)][civars.apply(row)].append([v])
        else:
            for (i, var) in sorted(legend.iteritems()):
                if DEP == var.vtype:
                    v = try_int_or_float(row[i])
                    master[cvars.apply(row)][civars.apply(row)][i].append(v)

except StopIteration:
    pass

###############################################################################
# Determine number of dependent variables and sample size.

sample_size = None
number_of_dvars = None

for (key, dataset) in sorted(master.iteritems()):
    for (iv, vars) in sorted(dataset.iteritems()):
        local_number_of_dvars = 0

        for var in vars:
            if isinstance(var, list): # Dependent variable
                local_number_of_dvars = local_number_of_dvars + 1

                if sample_size is None:
                    sample_size = len(var)
                    print sample_size
                else:
                    if sample_size is not len(var):
                        missing = abs(len(var) - sample_size)
                        print "WARNING: Missing "+str(missing)+" sample(s) "+\
                              "for ("+", ".join(str(x) for x in iv)+")"

        if number_of_dvars is None:
            number_of_dvars = local_number_of_dvars 
        else:
            assert number_of_dvars is local_number_of_dvars

###############################################################################
# Print the legend for the output data file and generate the GPI header

post_index = 0 

for (vindex, v) in sorted(legend.iteritems()):
    assert CTL == v.vtype or IND == v.vtype or DEP == v.vtype

    # For CTLs and INDs, we do no post-processing, so the 
    if CTL == v.vtype or IND == v.vtype:
        i0 = post_index

        print >> output_data, '## %s:%s:%s:%s' \
               % (vtype_to_str(v.vtype), v.tag, v.name, v.units)

        # The column indices in gnuplot start at 1, not 0 
        print >> output_header, '%s="%i"' % (v.tag, i0 + 1)

        post_index = post_index + 1

    else:
        i0 = post_index
        i1 = post_index + 1

        print >> output_data, '## %s:%s_AVG:%s - Average of %i Samples:%s'\
               % (vtype_to_str(v.vtype), v.tag, v.name, sample_size, v.units)
        print >> output_data, '## %s:%s_STD:%s - Standard Deviation:%s'\
               % (vtype_to_str(v.vtype), v.tag, v.name, v.units)

        print >> output_header, '%s_AVG="%i"' % (v.tag, i0 + 1) 
        print >> output_header, '%s_STD="%i"' % (v.tag, i1 + 1)

        post_index = post_index + 2

###############################################################################
# Print the output data set

datasets = sorted(master.iterkeys())

# Find distinguishing control variables (e.g. ones that AREN'T the same for all
# datasets).
dist_vars = find_distinguishing_variables(datasets)

is_first = True

for (key, dataset) in sorted(master.iteritems()):
    if not is_first: 
        print >> output_data
        print >> output_data
    else:
        is_first = False

    if len(datasets) > 1:
        if len(dist_vars) > 1:
            dist_keys = []

            for x in dist_vars:
                name  = legend[cvars.indices[x]].name
                units = legend[cvars.indices[x]].units

                if "" != units:
                    units = " [" + units + "]"

                dist_keys.append(name + ": " + str(key[x]) + units)
         
            print >> output_data, "\""+", ".join(dist_keys)+"\""
        else:
            name  = legend[cvars.indices[dist_vars[0]]].name
            units = legend[cvars.indices[dist_vars[0]]].units

            if "" != units:
                units = " [" + units + "]"

            dist_key = str(key[dist_vars[0]]) + units
         
            print >> output_data, "\""+dist_key+"\""

    # iv is a list, dvs is a list of lists.
    for (iv, vars) in sorted(dataset.iteritems()):
        for var in vars:
            if isinstance(var, list): # Dependent variable
                print >> output_data, mean(var), std(var),
            else: # Independent or control variable
                print >> output_data, var,

        print >> output_data

