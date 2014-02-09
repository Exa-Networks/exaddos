# encoding: utf-8
"""
reactor.py

Created by Thomas Mangin on 2014-02-07.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

import sys
import Queue

from .http import HTTPServer
from .snmp import SNMPClient
from .container import Container

# XXX: Look at ExaProxy Queue implementation
_queue = Queue.Queue()
_container = Container()

_server = None
_snmp = None

def setup (configuration):
	global _server
	global _snmp

	ip = configuration.http.host
	port = configuration.http.port
	_server = HTTPServer(configuration,_container)
	_server.add(ip,port,configuration.location.html,_queue)

	_snmp = SNMPClient(_container)
	interfaces = [_ for _ in configuration.keys() if _.isupper()]
	for interface in interfaces:
		_snmp.add(interface,configuration[interface],_queue)

def run ():
	print "starting snmp clients"
	_snmp.run()
	print "starting http server"
	_server.run()

	while True:
		try:
			exception = _queue.get(block=False)
		except Queue.Empty:
			pass
		except KeyboardInterrupt:
			break
		else:
			exc_type, exc_obj, exc_trace = exception
			raise exc_obj

		# print '.',
		# sys.stdout.flush()

		try:
			_server.join()
			if not _server.alive():
				print >> sys.stderr, "http server stopped / could not start, exiting"
				break
		except KeyboardInterrupt:
			break
		except Exception,e:
			print "exception ..." , e
			sys.stdout.flush()
			break

		if False:
			r = ''
			for link in _container.keys():
				r += '\n%s\n' % link
				for k,v in _container.get(link).iteritems():
					r += '   %-15s:%s\n' % (k,v)
			print r
			sys.stdout.flush()

	print "exiting ...."
	sys.stdout.flush()
	sys.stderr.flush()
