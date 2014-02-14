# encoding: utf-8
"""
container.py

Created by Thomas Mangin on 2014-02-06.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

# Ultimately these classes could use their own thread, a queue for local storage and redis as an option to allow multiple collection points

import sys
from threading import Lock
from copy import deepcopy

class ContainerSNMP (object):

	def __init__ (self,max_speakers=5):
		self.lock = Lock()
		self._data = {}

	def keys (self):
		with self.lock:
			return self._data.keys()

	def set (self,name,d):
		with self.lock:
			r = self._data.setdefault(name,{})
			for k,v in d.iteritems():
				r[k] = v

	def get (self,name):
		with self.lock:
			return dict(self._data[name].iteritems())

	def data (self):
		with self.lock:
			return deepcopy(self._data)


class ContainerFlow (object):

	def __init__ (self,max_speakers=5):
		self.lock = Lock()

		# flow code
		self._counters = {}
		self._overall = {}
		self._threshold = {}
		self._traffic = {}

		self._max_speaker = max_speakers
		self.period = 5

		self.localhost = (127 << 24) + 1

		for minute in range(0,self.period):
			self.make_minute(minute)

	def make_minute (self,minute):
		counter = self._counters

		if minute not in counter:
			counter[minute] = {}
			for direction in ('sipv4','dipv4'):
				for counter in ('bytes','pckts','flows'):
					# numbers need to be unique, and lower than our traffic
					self._threshold.setdefault(minute,{}).setdefault(direction,{})[counter] = list(range(-1,-self._max_speaker-1,-1))
					self._traffic.setdefault(minute,{}).setdefault(direction,{})[counter] = dict(zip(zip(range(-1,-self._max_speaker-1,-1),[minute,]*self._max_speaker),[self.localhost,]*self._max_speaker))

	def purge_minute (self,minute):
		counter = self._counters
		for past in self._threshold.keys()[:-self.period]:
			del counter[past]
			del self._threshold[past]
			del self._traffic[past]

	def ipfix (self,update):
		minute = int(update['epoch'])/60

		with self.lock:
			self.purge_minute(minute)
			self.make_minute(minute)

			overall = self._overall
			counter = self._counters

			bytes = update['bytes']
			pckts = update['pckts']
			flows = update['flows']
			proto = update['proto']

			total = overall.setdefault('total',{})
			total['bytes'] = total.get('bytes',0) + bytes
			total['pckts'] = total.get('pckts',0) + pckts
			total['flows'] = total.get('flows',0) + flows

			if update['proto'] == 6:  # TCP
				tcp = overall.setdefault('tcp',{})
				tcp['bytes'] = tcp.get('bytes',0) + bytes
				tcp['pckts'] = tcp.get('pckts',0) + pckts
				tcp['flows'] = tcp.get('flows',0) + flows
			elif update['proto'] == 17:  # UDP
				udp = overall.setdefault('udp',{})
				udp['bytes'] = udp.get('bytes',0) + bytes
				udp['pckts'] = udp.get('pckts',0) + pckts
				udp['flows'] = udp.get('flows',0) + flows
			else:
				other = overall.setdefault('other',{})
				other['bytes'] = other.get('bytes',0) + bytes
				other['pckts'] = other.get('pckts',0) + pckts
				other['flows'] = other.get('flows',0) + flows

			#source[time]['sipv4'/'dipv4'/'proto'][source ip]['pckts'/'bytes'/'flows']
			source = counter.setdefault(minute,{}).setdefault('sipv4',{}).setdefault(update['sipv4'],{'pckts': 0, 'bytes': 0, 'flows':0})
			source['bytes'] += bytes
			source['pckts'] += pckts
			source['flows'] += flows

			destination = counter.setdefault(minute,{}).setdefault('dipv4',{}).setdefault(update['dipv4'],{'pckts': 0, 'bytes': 0, 'flows':0})
			destination['bytes'] += bytes
			destination['pckts'] += pckts
			destination['flows'] += flows

			proto = counter.setdefault(minute,{}).setdefault('proto',{}).setdefault(update['proto'],{'pckts': 0, 'bytes': 0, 'flows':0})
			proto['bytes'] += bytes
			proto['pckts'] += pckts
			proto['flows'] += flows

			for direction,data in (('sipv4',source),('dipv4',destination)):
				for counter in ('bytes','pckts','flows'):
					traffic = self._traffic[minute][direction][counter]
					maximum = self._threshold[minute][direction][counter]
					ip = update['sipv4'] if direction == 'sipv4' else update['dipv4']
					value = data[counter]
					drop = maximum[0]

					if value > drop:
						traffic_items = list(traffic.iteritems())
						traffic_values, traffic_ips = zip(*traffic_items)
						traffic_number,traffic_minutes = zip(*traffic_values)

						# updating the number of <counter> seen for a ip
						if ip in traffic_ips:
							# key is a (value,time) tuple
							for key,host in traffic_items:
								if ip == host:
									traffic[key] = ip
									print "mb", maximum,key
									maximum = sorted(maximum + [value,])
									print "ma",maximum,key
									print
									break
						# replacing an entry with a new value
						else:
							print "MB",maximum,value
							maximum = sorted(maximum[1:] + [value,])
							print "MA",maximum,value
							print
							self._threshold[minute][direction][counter] = maximum

							for index,host in traffic_items:
								if ip == host: break

							timestamp = minute
							# prevent duplicate entries using a unique timestamp
							while timestamp in traffic_minutes:
								timestamp += 1

							# del traffic[drop]
							del self._traffic[minute][direction][counter][index]
							traffic[(value,timestamp)] = ip

	# def counters (self):
	# 	with self.lock:
	# 		return deepcopy(self._counters)

	def overall (self):
		with self.lock:
			return deepcopy(self._overall)

	def traffic (self):
		with self.lock:
			return deepcopy(self._traffic)
