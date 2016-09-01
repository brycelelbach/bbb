#! /usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
# Copyright (c) 2012-6 Bryce Adelstein Lelbach aka wash <brycelelbach@gmail.com>
#
# Distributed under the Boost Software License, Version 1.0. (See accompanying
# file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
###############################################################################

from sys import exit

from re import compile as regex_compile

# We take a single line as an input, and need to produce a tuple of cells. The
# input contains NO new lines and is NOT empty (so we assume it has at least
# one cell). The delimiter between cells is whitespace and multiple whitespace
# characters are collapsed. Cells which begin and end with quotations are
# strings and may contain whitespace.

# Precondition: line has been strip()'d and is not an empty string
class record_parser:
    engine = None

    ###########################################################################
    # Grammar

    def __init__(self):
        # Parse a quote character.
        quote_rule = r'["\']'

        # Parse a non-quote character or a quote character preceded by a
        # backslash.
        non_quote_rule = r'(?:.|(?:\\(?P=quote)))'

        # Parse a string cell.
        string_rule = r'(?P<quote>' + quote_rule + r')' \
                    + non_quote_rule + r'*?'            \
                    + r'(?P=quote)'

        # Parse a whitespace character.
        whitespace_rule = r'[ \t\r\n]'

        # Parse a non-whitespace character.
        non_whitespace_rule = r'[^ \t\r\n]'
        
        # Parse a cell.
        cell_rule = r'(?:' + string_rule + r')'            \
                  + r'|(?:' + non_whitespace_rule + r'+)'

        # Parse a record
        record_rule = r'(' + cell_rule + r')'           \
                    + r'(?:(?:' + whitespace_rule + r'+)|$)'

        self.engine = regex_compile(record_rule) 

    ###########################################################################

    def __call__(self, line):
        record = []

        match = self.engine.match(line)

        while match is not None:
            assert len(match.group(1)) is not 0
            record.append(match.group(1))
            match = self.engine.match(line, match.span()[1])

        print record

        assert len(record) is not 0

        return record

###############################################################################

parse_record = record_parser() 

###############################################################################

def print_function(v):
    print v

def should_assert(f, fail_msg):
    try:
        f()  

        print fail_msg
        exit(1)
    except AssertionError:
        pass

###############################################################################

should_assert(lambda: parse_record("") \
            , "ERROR: Empty line parsed.")

should_assert(lambda: parse_record(" ") \
            , "ERROR: 0-record line parsed.")

should_assert(lambda: parse_record("  ") \
            , "ERROR: 0-record line parsed.")

# This input contains a tab
should_assert(lambda: parse_record("	") \
            , "ERROR: 0-record line parsed.")

should_assert(lambda: parse_record("\n") \
            , "ERROR: 0-record line parsed.")

should_assert(lambda: parse_record(" \n") \
            , "ERROR: 0-record line parsed.")

###############################################################################

# Spaces delimiting
print parse_record("17 3.14 true 1e-07"      )
print parse_record("17 3.14 true 1e-07 "     ) # Spaces after
print parse_record("17 3.14 true 1e-07   "   ) # Spaces after
print parse_record("17 3.14 true 1e-07	"    ) # Tabs after
print parse_record("17 3.14 true 1e-07		") # Tabs after

should_assert(
    lambda: parse_record(     " 17 3.14 true 1e-07") \
  , "ERROR: Parsed unstripped record with a preceding space."
)
should_assert(
    lambda: parse_record(    "  17 3.14 true 1e-07") \
  , "ERROR: Parsed unstripped record with preceding spaces."
)
should_assert(
    lambda: parse_record(    "	17 3.14 true 1e-07") \
  , "ERROR: Parsed unstripped record with a preceding tab."
)
should_assert(
    lambda: parse_record("		17 3.14 true 1e-07") \
  , "ERROR: Parsed unstripped record with preceding tabs."
)

# Multiple spaces delimiting
print parse_record("17  3.14 true   1e-07"       )
print parse_record("17  3.14 true   1e-07 "      ) # Spaces after
print parse_record("17  3.14 true   1e-07   "    ) # Spaces after
print parse_record("17  3.14 true   1e-07	"    ) # Tabs after
print parse_record("17  3.14 true   1e-07		") # Tabs after

should_assert(
    lambda: parse_record(     " 17  3.14 true   1e-07") \
  , "ERROR: Parsed unstripped record with a preceding space."
)
should_assert(
    lambda: parse_record(    "  17  3.14 true   1e-07") \
  , "ERROR: Parsed unstripped record with preceding spaces."
)
should_assert(
    lambda: parse_record(    "	17  3.14 true   1e-07") \
  , "ERROR: Parsed unstripped record with a preceding tab."
)
should_assert(
    lambda: parse_record("		17  3.14 true   1e-07") \
  , "ERROR: Parsed unstripped record with preceding tabs."
)

# Tabs delimiting
print parse_record("17 3.14 true 1e-07"      )
print parse_record("17 3.14 true 1e-07 "     ) # Spaces after
print parse_record("17 3.14 true 1e-07   "   ) # Spaces after
print parse_record("17 3.14 true 1e-07	"    ) # Tabs after
print parse_record("17 3.14 true 1e-07		") # Tabs after

should_assert(
    lambda: parse_record(     " 17	3.14	true	1e-07") \
  , "ERROR: Parsed unstripped record with a preceding space."
)
should_assert(
    lambda: parse_record(    "  17	3.14	true	1e-07") \
  , "ERROR: Parsed unstripped record with preceding spaces."
)
should_assert(
    lambda: parse_record(    "	17	3.14	true	1e-07") \
  , "ERROR: Parsed unstripped record with a preceding tab."
)
should_assert(
    lambda: parse_record("		17	3.14	true	1e-07") \
  , "ERROR: Parsed unstripped record with preceding tabs."
)

# Multiple tabs delimiting
print parse_record("17		3.14	true			1e-07"       )
print parse_record("17		3.14	true			1e-07 "      ) # Spaces after
print parse_record("17		3.14	true			1e-07   "    ) # Spaces after
print parse_record("17		3.14	true			1e-07	"    ) # Tabs after
print parse_record("17		3.14	true			1e-07		") # Tabs after

should_assert(
    lambda: parse_record(     " 17		3.14	true			1e-07") \
  , "ERROR: Parsed unstripped record with a preceding space."
)
should_assert(
    lambda: parse_record(    "  17		3.14	true			1e-07") \
  , "ERROR: Parsed unstripped record with preceding spaces."
)
should_assert(
    lambda: parse_record(    "	17		3.14	true			1e-07") \
  , "ERROR: Parsed unstripped record with a preceding tab."
)
should_assert(
    lambda: parse_record("		17		3.14	true			1e-07") \
  , "ERROR: Parsed unstripped record with preceding tabs."
)

###############################################################################

print parse_record("'")
print parse_record("''")
print parse_record('"')
print parse_record('""')

print parse_record("\\\'")
print parse_record("\\\"")

print parse_record("'\\\''")
print parse_record('"\\\""')
print parse_record("'\\\"'")
print parse_record('"\\\'"')

print parse_record("3.14'")
print parse_record("3.14''")
print parse_record('3.14"')
print parse_record('3.14""')

print parse_record("'3.14")
print parse_record("''3.14")
print parse_record('"3.14')
print parse_record('""3.14')

print parse_record("3'14")
print parse_record("3''14")
print parse_record('3"14')
print parse_record('3""14')

print parse_record("'hello'")
print parse_record("'hello world'")
print parse_record("'hello' 'world'")

print parse_record("'hello world' 17 3.14 true 1e-07")
print parse_record("17 'hello world' 3.14 true 1e-07")
print parse_record("17 3.14 'hello world' true 1e-07")
print parse_record("17 3.14 true 'hello world' 1e-07")
print parse_record("17 3.14 true 1e-07 'hello world'")

print parse_record("17 3.14 true 1e-07 'hello world' ")


