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
from .log import log,err

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
									err('warning, ipfix data is generated faster than we can consumme, %d messages queued' % size)
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
		log('starting ipfix consummer')
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
		# The best a 10 Mb interface can do is 14,880 frames per second
		# each frame being only 84 bytes
		# On 127.0.0.1, my Mac can receive around 10/12k frames ..
		# So it would seems the MAC loopback is bad for high perf networking ...
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			current = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)  # value of 196724 on my mac
			new = current
			while True:
				try:
					new += current
					sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, new)
				except socket.error:
					log('ipfix changed SO_RCVBUF from %d to %d' % (current,new-current))
					sys.stdout.flush()
					break

			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.bind((self.host,self.port))
			self.running = True
		except:
			err('could not start ipfix server')
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
		log('starting ipfix server')
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
			# start 3 consumers per ipfix server
			for index in range(3):
				consumer = _FlowServerConsumer(queue,self.container,raising)
				consumer.parent = self
				self.consumer[key+str(index)] = consumer

			server = _FlowServerFactory(host,port,queue,raising)
			server.parent = self
			self.servers[key] = server

	def run (self,daemon):
		for key in self.consumer:
			if daemon and self.consumer[key].use_thread:
				self.consumer[key].start()
			if not daemon and not self.consumer[key].use_thread:
				self.consumer[key].start()

		for key in self.servers:
			if daemon and self.servers[key].use_thread:
				self.servers[key].start()
			if not daemon and not self.servers[key].use_thread:
				self.servers[key].start()

	def join (self):
		for key in self.servers:
			self.servers[key].join()

	def alive (self):
		for key in self.servers:
			if self.servers[key].flowd.isAlive():
				return True
		return False
