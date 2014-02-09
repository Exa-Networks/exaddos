# encoding: utf-8
"""
snmp.py

Created by Thomas Mangin on 2014-02-07.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

import sys
import time
import random

from .thread import Thread
from .warning import unicast,notunicast,bw


class _SNMPFactory (object):
	initialised = False

	correction = {
		'ifHCInOctets'    : 8,
		'ifHCInUcastPkts' : 1,
		'ifInNUcastPkts'  : 1,
		'ifInErrors'      : 1,
		'ifInDiscards'    : 1,
		}

	unit = {
		'ifHCInOctets'    : 'bits',
		'ifHCInUcastPkts' : 'pkts',
		'ifInNUcastPkts'  : 'pkts',
		'ifInErrors'      : 'pkts',
		'ifInDiscards'    : 'pkts',
		}

	def __init__ (self,name,interface,container,queue):
		self.name = name
		self.interface = interface
		self.container = container
		self.queue = queue

		from pysnmp.smi import builder

		mibBuilder = builder.MibBuilder().loadModules('SNMPv2-MIB', 'IF-MIB')

		self.collection = {
			'ifHCInOctets'    : mibBuilder.importSymbols('IF-MIB', 'ifHCInOctets')[0].getName() + (self.interface.snmp_index_port,),
			'ifHCInUcastPkts' : mibBuilder.importSymbols('IF-MIB', 'ifHCInUcastPkts')[0].getName() + (self.interface.snmp_index_vlan,),
			'ifInNUcastPkts'  : mibBuilder.importSymbols('IF-MIB', 'ifInNUcastPkts')[0].getName() + (self.interface.snmp_index_vlan,),
			'ifInErrors'      : mibBuilder.importSymbols('IF-MIB', 'ifInErrors')[0].getName() + (self.interface.snmp_index_vlan,),
			'ifInDiscards'    : mibBuilder.importSymbols('IF-MIB', 'ifInDiscards')[0].getName() + (self.interface.snmp_index_vlan,),
			'sysDescr'        : mibBuilder.importSymbols('SNMPv2-MIB', 'sysDescr')[0].getName() + (0,),
		}

		self.description = str(self._get('sysDescr') or '-')

	def _get (self,key):
		from pysnmp.entity.rfc3413.oneliner import cmdgen
		from pysnmp.error import PySnmpError

		try:
			if self.interface.snmp_version == 2:
				errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(
					cmdgen.CommunityData('exaddos', self.interface.snmp_password),
					cmdgen.UdpTransportTarget((self.interface.router, 161)),
					self.collection[key]
				)
			else:
				raise NotImplemented('Feel free to add support for this SNMP version and send us the patch - thanks')
		except PySnmpError:
			print >> sys.stderr, 'SNMP collection failed for %s %s' % (self.name,key)
			sys.stderr.flush()
			return None

		if (errorIndication,errorStatus,errorIndex) == (None,0,0):
			try:
				return varBinds[0][1]
			# The data was of type NoSuchInstance
			except AttributeError:
				print >> sys.stderr, 'SNMP: %s did not have %s' % (self.name,key)
				sys.stderr.flush()
				return None
		else:
			print >> sys.stderr, 'SNMP collection failed for %s %s' % (self.name,key)
			sys.stderr.flush()
			return None

	def collect (self):
		result = {}

		for key in self.correction:
			value = self._get(key)
			if value is not None:
				result[key] = long(value) * self.correction[key] / self.interface.snmp_frequency
			else:
				result[key] = -1

		return result

	def serve (self):
		last = self.collect()

		values = dict(zip(last.keys(),[0] * len(last.keys())))
		values['description'] = self.description
		values['duration'] = 0
		self.container.set(self.name,values)

		delay = random.randrange(0,self.interface.snmp_frequency*100) / 100.0
		# make sure we are spending the SNMP requests
		time.sleep(delay)

		while True:
			start = time.time()

			new = self.collect()

			values['description'] = self.description
			values['duration'] = float('%.2f' % max(0,time.time() - start))

			for key in self.correction:
				if new[key] == -1:
					values[key] = -1
				else:
					value = new[key] - last[key]
					values[key] = value
					#formated(value,self.unit[key])

			values['warning'] = True if unicast(values,self.interface) or notunicast(values,self.interface) or bw(values,self.interface) else False

			self.container.set(self.name,values)
			last = new

			sleep = max(0,self.interface.snmp_frequency+start-time.time())
			time.sleep(sleep)

	def start (self):
		self.snmp = Thread(self.serve,self.queue)
		self.snmp.daemon = True
		self.snmp.start()

	def join (self):
		if self.snmp:
			self.snmp.join(0.1)

class SNMPClient (object):
	clients = {}
	counter = 0

	def __init__ (self,container):
		# This will be shared among all instrance
		self.container = container

	def add (self,name,interface,queue):
		host = interface.router
		key = '%s:%d' % (host,self.counter)
		self.counter += 1
		client = _SNMPFactory(name,interface,self.container,queue)
		client.parent = self
		self.clients[key] = client

	def run (self):
		for key in self.clients:
			self.clients[key].start()

	def join (self):
		for key in self.clients:
			self.clients[key].join()

	def alive (self):
		for key in self.clients:
			if self.clients[key].snmp.isAlive():
				return True
		return False
