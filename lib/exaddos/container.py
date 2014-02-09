# encoding: utf-8
"""
container.py

Created by Thomas Mangin on 2014-02-06.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

from threading import Lock
from copy import deepcopy

class Container (object):
	data = {}
	lock = Lock()

	def keys (self):
		with self.lock:
			return self.data.keys()

	def set (self,name,d):
		with self.lock:
			r = self.data.setdefault(name,{})
			for k,v in d.iteritems():
				r[k] = v

	def get (self,name):
		with self.lock:
			return dict(self.data[name].iteritems())

	def duplicate (self):
		with self.lock:
			return deepcopy(self.data)
