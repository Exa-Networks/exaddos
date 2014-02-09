#!/usr/bin/env python
# encoding: utf-8
"""
records.py

Created by Thomas Mangin on 2012-05-12.
Copyright (c) 2012 Exa Networks. All rights reserved.
"""

import sqlite3

class Records (object):
	def __init__ (self,configuration):
		self.configuration = configuration

	def locate (self,dialed):
		try:
			connection = sqlite3.connect(self.configuration.enum.database)
			cursor = connection.cursor()
			cursor.execute('select context,destination from phone where number = ?',(dialed,))
			result = cursor.fetchone()
			connection.close()
		except sqlite3.Error:
			return self.configuration.service.media,'%s@%s' % (self.configuration.message.error.replace('#<number>','00%s' % dialed), self.configuration.gateway.media)

		# We found the number
		if result:
			if '@' in result or '%' in result:
				return str(result[0]),str(result[1])
			return str(result[0]),'00%s@%s' % (dialed,result[1])

		try:
			connection = sqlite3.connect(self.configuration.enum.database)
			cursor = connection.cursor()
			cursor.execute('select * from allocation where start <= ? and end >= ?',(dialed,dialed))
			result = cursor.fetchone()
			connection.close()
		except sqlite3.Error:
			return self.configuration.service.media,'%s@%s' % (self.configuration.message.error.replace('#<number>','00%s' % dialed), self.configuration.gateway.media)

		# If the number is local then let the caller know it is unassigned
		if result:
			return self.configuration.service.media,'%s@%s' % (self.configuration.message.unallocated.replace('#<number>','00%s' % dialed), self.configuration.gateway.media)

		# the number is not local, send to PSTN
		return self.configuration.service.pstn, '00%s@%s' % (dialed,self.configuration.gateway.pstn)
