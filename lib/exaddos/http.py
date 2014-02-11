# encoding: utf-8
"""
http.py

Created by Thomas Mangin on 2014-02-06.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

import os
import urlparse
import SimpleHTTPServer
import SocketServer
import json
import locale

from .thread import Thread

locale.setlocale(locale.LC_ALL, 'en_US')

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
				if type(v) in (type(0), type(0L)):
					d[k] = locale.format("%d", v, grouping=True)
				else:
					d[k] = v
			r.append(d)
	return json.dumps(r)


class HTTPHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
	# index is added to this class
	# container is added to this class

	def log_message (*args):
		pass

	def do_POST (self):
		self.send_response(200)
		self.send_header('Content-type', 'text/json')
		self.end_headers()
		self.wfile.write(json.dumps(self.container.duplicate()))
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
			if path == "/json/snmp.json":
				code = 200
				encoding = 'text/json'
				content = snmp_json(self.container.duplicate())

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
			fname = os.path.join(self.location,path.lstrip('/'))

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

	def __init__ (self,configuration,container):
		HTTPHandler.location = configuration.location.html
		# This will be shared among all instrance
		HTTPHandler.container = container


	def add (self,host,port,index,queue):
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
