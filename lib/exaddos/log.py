# encoding: utf-8
"""
log.py

Created by Thomas Mangin on 2014-02-18.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

import sys
from threading import Lock


__loud = {
	'stdout': True,
	'stderr': True,
}

__lock = Lock()

def log (string):
	if __loud['stdout']:
		with __lock:
			sys.stdout.write('%s\n' % string)
			sys.stdout.flush()

def err (string):
	if __loud['stderr']:
		with __lock:
			sys.stderr.write('%s\n' % string)
			sys.stderr.flush()

def silence ():
	__loud['stdout'] = False
