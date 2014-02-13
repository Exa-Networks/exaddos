# encoding: utf-8
"""
http.py

Created by Thomas Mangin on 2014-02-06.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

import os
import sys
import urlparse
import SimpleHTTPServer
import SocketServer
import json
import socket
import struct

from .thread import Thread

def nop (arg):
	return arg

def snmp_json (data):
	s = {}
	for link,information in data.iteritems():
		s.setdefault(information['ifHCInUcastPkts'] + information['ifInNUcastPkts'],[]).append(link)

	display = sorted(s.keys())
	display.reverse()
	r = []
	for speed in display:
		links = s[speed]
		for link in sorted(links):
			d = {'link':link}
			information = data[link]
			for k,v in information.iteritems():
				d[k] = v
			r.append(d)
	return json.dumps(r)

def flow_overall (data):
	r = {}
	for proto in data:
		for counter in data[proto]:
			r["%s_%s" % (proto,counter)] = data[proto][counter]
	return json.dumps(r)

def flow_traffic (data,direction,counter):
	r = {}
	for t in data:
		for d in data[t]:
			if d != direction: continue
			for c in data[t][d]:
				if c != counter: continue
				info = data[t][d][c]
				for number in info:
					if number < 0: continue
					ip = socket.inet_ntoa(struct.pack("!I", info[number]))
					if ip not in r: r[ip] = {'value':0}
					r[ip]['ip'] = ip
					r[ip]['value'] += info[number]
	return json.dumps(list(r.itervalues()))

class HTTPHandler (SimpleHTTPServer.SimpleHTTPRequestHandler):
	# webroot is added to this class
	# snmp is added to this class
	# flow is added to this class

	# monkey patching 3.3 fix http://hg.python.org/cpython/rev/7e5d7ef4634d
	def finish (self):
		try:
			SimpleHTTPServer.SimpleHTTPRequestHandler.finish(self)
		except socket.error:
			# should really check it is really ECONNABORTED
			pass

	def __init__ (self,*args,**kargs):
		self._json = {
			"/json/"                                 : ( 'text/json', json.dumps,     self.json_list,    () ),
			"/json/snmp/data.json"                   : ( 'text/json', json.dumps,     self.snmp.data,    () ),
			"/json/snmp/interfaces.json"             : ( 'text/json', snmp_json ,     self.snmp.data,    () ),
			"/json/flow/overall.json"                : ( 'text/json', json.dumps,     self.flow.overall, () ),
			"/json/flow/overall.summary.json"        : ( 'text/json', flow_overall,   self.flow.overall, () ),
			"/json/flow/traffic.json"                : ( 'text/json', json.dumps,     self.flow.traffic, () ),
			"/json/flow/traffic.listener.pckts.json" : ( 'text/json', flow_traffic,   self.flow.traffic, ('sipv4','pckts') ),
			"/json/flow/traffic.listener.bytes.json" : ( 'text/json', flow_traffic,   self.flow.traffic, ('sipv4','bytes') ),
			"/json/flow/traffic.listener.flows.json" : ( 'text/json', flow_traffic,   self.flow.traffic, ('sipv4','flows') ),
			"/json/flow/traffic.speaker.pckts.json"  : ( 'text/json', flow_traffic,   self.flow.traffic, ('dipv4','pckts') ),
			"/json/flow/traffic.speaker.bytes.json"  : ( 'text/json', flow_traffic,   self.flow.traffic, ('dipv4','bytes') ),
			"/json/flow/traffic.speaker.flows.json"  : ( 'text/json', flow_traffic,   self.flow.traffic, ('dipv4','flows') ),
		}
		try:
			SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self,*args,**kargs)
		except socket.error:
			# should really check it is really ECONNABORTED
			pass

	def json_list (self):
		r = []
		for name in self._json:
			r.append(name)
		return r

	def log_message (*args):
		pass

	def do_POST (self):
		return

	def valid_path (self,path):
		for letter in path:
			if letter.isalnum():
				continue
			if letter in ('-','_','.','/'):
				continue
			return False

		return '..' not in path

	def do_GET (self):
		content = ''
		fname = ''

		# Parse query data to find out what was requested
		parsedParams = urlparse.urlparse(self.path)

		path = parsedParams.path

		if path.startswith('/json/'):
			code = 200

			if path in self._json:
				encoding, presentation, source, param = self._json[path]
				content = presentation(source(),*param)
			else:
				code = 404
				encoding = 'text/html'
				content = '404'

		elif self.valid_path(path):
			if path == '/':
				path = '/index.html'
			code = 200
			if path.endswith('.js'):
				encoding = 'application/x-javascript'
			elif path.endswith('.html'):
				encoding = 'text/html'
			elif path.endswith('.css'):
				encoding = 'text/css'
			elif path.endswith(('.jpg','.jpeg')):
				encoding = 'image/jpeg'
			elif path.endswith('.png'):
				encoding = 'image/png'
			elif path.endswith('.gif'):
				encoding = 'image/gif'
			else:
				encoding = 'text/plain'
			fname = os.path.join(self.webroot,path.lstrip('/'))

			if fname and os.path.isfile(fname):
				try:
					with open(fname,'r') as f:
						content = f.read()
				except Exception:
					code = 500
					encoding = 'text/html'
					content = 'could not read the file'
			else:
				code = 404
				encoding = 'text/html'
				content = '404'

		else:
			code = 404
			encoding = 'text/html'
			content = '404'

		if code == 404:
			print >> sys.stderr, 'http server could not serve path %s' % path
			sys.stderr.flush()

		self.send_response(code)
		self.send_header('Content-type', encoding)
		self.end_headers()
		self.wfile.write(content)

		return


class _HTTPServerFactory (object):
	def __init__ (self,host,port,queue):
		print 'http server on %s:%d' % (host,port)
		self.httpd = None
		self.queue = queue

		self.host = host
		self.port = port

	def serve (self):
		SocketServer.TCPServer.allow_reuse_address = True
		server = SocketServer.TCPServer((self.host, self.port),HTTPHandler)
		server.serve_forever()

	def start (self):
		self.httpd = Thread(self.serve,self.queue)
		self.httpd.daemon = True
		self.httpd.start()

	def join (self):
		if self.httpd:
			self.httpd.join(0.1)


class HTTPServer (object):
	servers = {}

	def __init__ (self,configuration,snmp,flow):
		HTTPHandler.webroot = configuration.location.html
		# This will be shared among all instrance
		HTTPHandler.snmp = snmp
		HTTPHandler.flow = flow

	def add (self,host,port,queue):
		key = '%s:%d' % (host,port)
		if key not in self.servers:
			server = _HTTPServerFactory(host,port,queue)
			server.parent = self
			self.servers[key] = server

	def run (self):
		for key in self.servers:
			self.servers[key].start()

	def join (self):
		for key in self.servers:
			self.servers[key].join()

	def alive (self):
		for key in self.servers:
			if self.servers[key].httpd.isAlive():
				return True
		return False
