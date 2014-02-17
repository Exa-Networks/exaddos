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

# group the OID to request
# http://pysnmp.sourceforge.net/docs/current/apps/sync-command-generator.html

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

	def __init__ (self,name,interface,container,raising):
		self.name = name
		self.interface = interface
		self.container = container
		self.raising = raising
		self.running = None

	def _get (self,key):
		from pysnmp.entity.rfc3413.oneliner import cmdgen
		from pysnmp.error import PySnmpError
		from pysnmp.proto.rfc1905 import NoSuchInstance

		try:
			if self.interface.snmp_version == 2:
				errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(
					cmdgen.CommunityData('exaddos', self.interface.snmp_password),
					cmdgen.UdpTransportTarget((self.interface.router, 161)),
					self.collection[key]
				)
			elif self.interface.snmp_version == 3:
				from pysnmp.entity import config

				mapping_auth = {
					'MD5' : config.usmHMACMD5AuthProtocol,
					'SHA' : config.usmHMACSHAAuthProtocol,
					''    : config.usmNoAuthProtocol,
				}

				mapping_privacy = {
					'DES'     : config.usmDESPrivProtocol,
					'3DES'    : config.usm3DESEDEPrivProtocol,
					'AES-128' : config.usmAesCfb128Protocol,
					'AES-192' : config.usmAesCfb192Protocol,
					'AES-256' : config.usmAesCfb256Protocol,
					''        : config.usmNoPrivProtocol,
				}

				user = cmdgen.UsmUserData(
						self.interface.snmp_user,
						self.interface.snmp_auth_key,
						self.interface.snmp_privacy_key,
						authProtocol=mapping_auth[self.interface.snmp_auth_method],
						privProtocol=mapping_privacy[self.interface.snmp_privacy_method])

				transport = cmdgen.UdpTransportTarget((self.interface.router, 161))

				errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(
					user, transport,
					self.collection[key]
				)
#					cmdgen.MibVariable('.'.join(str(_) for _ in self.collection[key]))
			else:
				raise NotImplemented('Feel free to add support for this SNMP version and send us the patch - thanks')
		except PySnmpError:
			print >> sys.stderr, 'SNMP collection failed for %s %s' % (self.name,key)
			sys.stderr.flush()
			return None

		if (errorIndication,errorStatus,errorIndex) == (None,0,0):
			result = varBinds[0][1]

			if isinstance(result,NoSuchInstance):
				print >> sys.stderr, 'SNMP: %s did not have %s' % (self.name,key)
				sys.stderr.flush()
				return None

			try:
				return varBinds[0][1]
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

		raise Exception('')

		for key in self.correction:
			value = self._get(key)
			if value is not None:
				result[key] = long(value) * self.correction[key] / self.interface.snmp_frequency
			else:
				result[key] = -1

		return result

	def serve (self):
		if self.running is None:
			return self._init()
		return self._serve()

	def _init (self):
		from pysnmp.smi import builder

		mibBuilder = builder.MibBuilder().loadModules('SNMPv2-MIB', 'IF-MIB')

		self.collection = {
			'ifHCInOctets'    : mibBuilder.importSymbols('IF-MIB', 'ifHCInOctets')[0].getName() + (self.interface.snmp_index_vlan,),
			'ifHCInUcastPkts' : mibBuilder.importSymbols('IF-MIB', 'ifHCInUcastPkts')[0].getName() + (self.interface.snmp_index_vlan,),
			'ifInNUcastPkts'  : mibBuilder.importSymbols('IF-MIB', 'ifInNUcastPkts')[0].getName() + (self.interface.snmp_index_port,),
			'ifInErrors'      : mibBuilder.importSymbols('IF-MIB', 'ifInErrors')[0].getName() + (self.interface.snmp_index_port,),
			'ifInDiscards'    : mibBuilder.importSymbols('IF-MIB', 'ifInDiscards')[0].getName() + (self.interface.snmp_index_port,),
			'sysDescr'        : mibBuilder.importSymbols('SNMPv2-MIB', 'sysDescr')[0].getName() + (0,),
		}

		try:
			self.description = str(self._get('sysDescr') or '-')
			self.running = True
		except KeyboardInterrupt:
			self.running = False

	def _serve (self):
		last = self.collect()

		values = dict(zip(last.keys(),[0] * len(last.keys())))
		values['description'] = self.description
		values['duration'] = 0
		self.container.set(self.name,values)

		delay = random.randrange(0,self.interface.snmp_frequency*100) / 100.0
		# make sure we are spending the SNMP requests
		time.sleep(delay)

		print >> sys.stderr, 'snmp poller starting %s' % self.name
		sys.stderr.flush()

		while self.running:
			start = time.time()

			try:
				new = self.collect()
			except KeyboardInterrupt:
				self.running = False
				continue

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

		print >> sys.stderr, 'snmp poller ended %s' % self.name
		sys.stderr.flush()

	def start (self):
		print "starting snmp clients"
		sys.stdout.flush()
		self.snmp = Thread(self.serve,self.raising)
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

	def add (self,name,interface,raising):
		host = interface.router
		key = '%s:%d' % (host,self.counter)
		self.counter += 1
		client = _SNMPFactory(name,interface,self.container,raising)
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
