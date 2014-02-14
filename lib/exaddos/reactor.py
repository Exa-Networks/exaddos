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
	# we start one thread per router
	# therefore stopping threads for debugging can not be a on/off thing
	_snmp.run()

	_flow.run(daemon=True)
	_http.run(daemon=True)

	# _flow.run(daemon=False)
	# _http.run(daemon=False)

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


# from: http://stackoverflow.com/questions/132058/showing-the-stack-trace-from-a-running-python-application
# import threading, sys, traceback

# def dumpstacks(signal, frame):
# 	id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
# 	code = []
# 	for threadId, stack in sys._current_frames().items():
# 		code.append("\n# Thread: %s(%d)" % (id2name.get(threadId,""), threadId))
# 		for filename, lineno, name, line in traceback.extract_stack(stack):
# 			code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
# 			if line:
# 				code.append("  %s" % (line.strip()))
# 	print "\n".join(code)

# import signal
# signal.signal(signal.SIGQUIT, dumpstacks)
