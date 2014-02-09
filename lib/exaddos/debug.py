# encoding: utf-8
"""
debug.py

Created by Thomas Mangin on 2014-02-06.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

import os
import sys

import traceback

def bug_report (type, value, trace):
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-'*80
	print >> sys.stderr, '-- Please provide the information below: https://github.com/Exa-Networks/exaddos'
	print >> sys.stderr, '-'*80
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-- Version'
	print >> sys.stderr, ''
	print >> sys.stderr, sys.version
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-- Traceback'
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	traceback.print_exception(type,value,trace)
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-'*80
	print >> sys.stderr, '-- Please provide the information above: https://github.com/Exa-Networks/exaddos'
	print >> sys.stderr, '-'*80
	print >> sys.stderr, ''
	print >> sys.stderr, ''

	#print >> sys.stderr, 'the program failed with message :', value

def intercept (type, value, trace):
	interactive = os.environ.get('PDB',None)

	if interactive in ['0','']:
		# PDB was set to 0 or '' which is undocumented, and we do nothing
		pass
	else:
		bug_report(type, value, trace)
		if interactive == 'true':
			import pdb
			pdb.pm()

sys.excepthook = intercept

if sys.argv:
	del sys.argv[0]
	__file__ = os.path.abspath(sys.argv[0])
	__name__ = '__main__'
	execfile(sys.argv[0])
