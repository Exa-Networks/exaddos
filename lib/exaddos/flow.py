# encoding: utf-8
"""
flow.py

Created by Thomas Mangin on 2014-02-09.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

import sys
import socket
import time

from .thread import Thread
from .ipfix import IPFIX
from .q import Queue,Empty

class _FlowServerConsumer (object):
	use_thread = True

	def __init__ (self,queue,container,raising):
		self.consumerd = None
		self.queue = queue
		self.container = container
		self.raising = raising
		self.parser = IPFIX(container.ipfix)
		self.running = True

	def serve (self):
		last = time.time() - 10
		if self.use_thread:
			try:
				while self.running:
					try:
						while True:
							size = self.queue.qsize()
							if size > 1000:
								now = time.time()
								if now - last > 1:
									print >> sys.stderr, 'warning, ipfix data is generated faster than we can consumme, %d messages queued' % size
									sys.stderr.flush()
									last = now
							data = self.queue.get()
							self.parser.read(data)
					except Empty:
						pass
			except Exception,e:
				self.running = False
				raise e
		else:
			# debug without starting a thread
			while self.running:
				try:
					while True:
						data = self.queue.get()
						self.parser.read(data)
				except Empty:
					pass

	def start (self):
		print "starting ipfix consummer"
		if self.use_thread:
			self.consumerd = Thread(self.serve,self.raising)
			self.consumerd.daemon = True
			self.consumerd.start()
		else:
			self.serve()

	def alive (self):
		return self.running

	def join (self):
		if self.consumerd:
			self.consumerd.join(0.1)

class _FlowServerFactory (object):
	use_thread = True

	def __init__ (self,host,port,queue,raising):
		self.host = host
		self.port = port
		self.queue = queue
		self.raising = Queue()
		self.running = True

	def serve (self):
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.bind((self.host,self.port))
			self.running = True
		except:
			print >> sys.stderr, 'could not start ipfix server'
			raise

		if self.use_thread:
			try:
				while self.running:
					data, addr = sock.recvfrom(8192)
					data = self.queue.put(data)
			except Exception,e:
				self.running = False
				raise e
		else:
			# debug without starting a thread
			while self.running:
				data, addr = sock.recvfrom(8192)
				data = self.queue.put(data)

	def start (self):
		print "starting ipfix server"
		if self.use_thread:
			self.flowd = Thread(self.serve,self.raising)
			self.flowd.daemon = True
			self.flowd.start()
		else:
			self.serve()

	def alive (self):
		return self.running

	def join (self):
		if self.flowd:
			self.flowd.join(0.1)


class FlowServer (object):
	servers = {}
	consumer = {}

	def __init__ (self,configuration,container):
		# This will be shared among all instrance
		self.configuration = configuration
		self.container = container

	def add (self,host,port,raising):
		queue = Queue()

		key = '%s:%d' % (host,port)
		if key not in self.servers:
			consumer = _FlowServerConsumer(queue,self.container,raising)
			consumer.parent = self
			self.consumer[key] = consumer

			server = _FlowServerFactory(host,port,queue,raising)
			server.parent = self
			self.servers[key] = server

	def run (self,daemon):
		for key in self.servers:
			if daemon and self.servers[key].use_thread:
				self.consumer[key].start()
				self.servers[key].start()
			if not daemon and not self.servers[key].use_thread:
				self.consumer[key].start()
				self.servers[key].start()

	def join (self):
		for key in self.servers:
			self.servers[key].join()

	def alive (self):
		for key in self.servers:
			if self.servers[key].flowd.isAlive():
				return True
		return False
