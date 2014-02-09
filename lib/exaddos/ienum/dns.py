#!/usr/bin/env python
# encoding: utf-8
"""
server.py

Created by Thomas Mangin on 2012-05-12.
Copyright (c) 2012 Exa Networks. All rights reserved.
"""

GATEWAY = "sip-border3.aql.com"
UNALLOCATED_URI = "unallocated-%s@82.219.4.166"
NOTFOUND_URI = "not-found@82.219.4.166"

import time

from twisted.internet.protocol import Factory, Protocol
from twisted.internet import defer

from twisted.names import server
from twisted.names import dns

from ienum.records import Records

class DNSServerFactory(server.DNSServerFactory):
	def handleQuery(self, message, protocol, address):
		domain = self.configuration.dns.domain

		# handle only the first query in the request
		query = message.queries[0]
		lookup = str(query.name)

		if query.type != dns.NAPTR:
			print 'ignoring non NAPTR ', str(query)
			self._reply(message,protocol,address,lookup,None,'',query.type)
			return

		if not lookup.endswith(domain):
			print 'wrong enum domain in',lookup
			self._reply(message,protocol,address,lookup,None,query.type)
			return

		dialed = ''.join(n for n in lookup[:-len(domain)].split('.')[::-1])

		print time.strftime('%Y-%m-%d  %H:%M:%S',time.localtime()), str(address[0]), 'requested', dialed

		if not dialed.isdigit():
			# should never occurs !
			print "is not a digit"
			self._reply(message,protocol,address,lookup,None)
			return

		service,endpoint = self.records.locate(dialed)
		print time.strftime('%Y-%m-%d  %H:%M:%S',time.localtime()), dialed, 'goes to', endpoint
		self._reply(message,protocol,address,lookup,endpoint,service)

	def _reply (self,message,protocol,address,lookup,response,service='',packet=dns.NAPTR):
		if response and packet == dns.NAPTR:
			payload = dns.Record_NAPTR(
				order=10,
				preference=100,
				flags='U',
				service='E2U+sip' + ':%s' % service.upper() if service else '',
				regexp='!^.*$!sip:'+response+'!',
				replacement='',
				ttl=300)
			ttl = self.configuration.dns.ttl
		else:
			print >> sys.stderr, 'no reply send, invalid DNS request'
			payload =  None
			ttl = 10

		rr = dns.RRHeader(lookup,type=packet,payload=payload,ttl=ttl)

		d = defer.Deferred()
		d.addCallback(self.gotResolverResponse, protocol, message, address)
		reactor.callLater(0, d.callback, ([rr], [], []))

from twisted.names import dns
from twisted.names import client
from twisted.internet import reactor



_resolvers = {}
def resolverFactory (resolver):
	if resolver not in _resolvers:
		_resolvers[resolver] = client.Resolver(servers=[resolver])
	return _resolvers[resolver]

# If speed becomes an issue we may be able to remove contention for access to the DB using multiple factories
_factories = {}
def setupFactory (configuration,resolver,verbosity):
	ip = configuration.dns.host
	port = configuration.dns.port
	if ip in _factories:
		return
	factory = DNSServerFactory(clients=[resolverFactory(resolver)], verbose=verbosity)
	factory.noisy = verbosity

	factory.configuration = configuration
	factory.records = Records(configuration)

	reactor.listenTCP(port, factory, interface=ip)
	_factories[ip] = factory

def setupProtocol (ip,port,verbosity):
	if not ip in _factories:
		return
	protocol = dns.DNSDatagramProtocol(_factories[ip])
	protocol.noisy = verbosity
	reactor.listenUDP(port, protocol, interface=ip)

def setup (configuration):
	ip = configuration.dns.host
	port = configuration.dns.port
	resolver = ('127.0.0.1',53)
	verbosity = 0
	if ip in _factories:
		return
	setupFactory(configuration,resolver,verbosity)
	setupProtocol(ip,port,verbosity)

