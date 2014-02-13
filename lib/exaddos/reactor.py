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
from .flow import FlowServer
from .container import ContainerSNMP,ContainerFlow

# XXX: Look at ExaProxy Queue implementation
_queue = Queue.Queue()
_snmp_container = ContainerSNMP()
_flow_container = ContainerFlow()

_http = None
_flow = None
_snmp = None

def setup (configuration):
	global _http
	global _flow
	global _snmp

	ip = configuration.http.host
	port = configuration.http.port
	_http = HTTPServer(configuration,_snmp_container,_flow_container)
	_http.add(ip,port,_queue)

	_snmp = SNMPClient(_snmp_container)
	interfaces = [_ for _ in configuration.keys() if _.isupper()]
	for interface in interfaces:
		_snmp.add(interface,configuration[interface],_queue)

	ip = configuration.ipfix.host
	port = configuration.ipfix.port
	_flow = FlowServer(configuration,_flow_container)
	_flow.add(ip,port,_queue)


def run ():
	print "starting snmp clients"
	_snmp.run()
	print "starting ipfix server"
	_flow.run()
	print "starting http server"
	_http.run()

	# import pdb; pdb.set_trace()

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
			_http.join()
			if not _http.alive():
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
			for link in _snmp_container.keys():
				r += '\n%s\n' % link
				for k,v in _snmp_container.get(link).iteritems():
					r += '   %-15s:%s\n' % (k,v)
			print r
			sys.stdout.flush()

	print "exiting ...."
	sys.stdout.flush()
	sys.stderr.flush()
