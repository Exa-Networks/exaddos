# encoding: utf-8
"""
container.py

Created by Thomas Mangin on 2014-02-06.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

# Ultimately these classes could use their own thread, a queue for local storage and redis as an option to allow multiple collection points

from threading import Lock
from copy import deepcopy
from time import time

class ContainerSNMP (object):

	def __init__ (self,max_speakers=5):
		self._lock = Lock()
		self._data = {}

	def keys (self):
		with self._lock:
			return self._data.keys()

	def set (self,name,d):
		with self._lock:
			r = self._data.setdefault(name,{})
			for k,v in d.iteritems():
				r[k] = v

	def get (self,name):
		with self._lock:
			return dict(self._data[name].iteritems())

	def data (self):
		with self._lock:
			return deepcopy(self._data)


class ContainerFlow (object):
	retain = 60

	def __init__ (self,max_speakers=5):
		self._traffic_lock = Lock()

		# flow code
		self._counters = {}
		self._overall = {}
		self._threshold = {}
		self._traffic = {}

		self._monitor_lock = Lock()
		self._monitor = {}
		self._monitored = {}

		self._max_speaker = max_speakers
		self.period = 5

		for minute in range(0,self.period):
			self.make_minute(minute)

	def make_minute (self,minute):
		counter = self._counters

		default = {
			'sipv4' : (127 << 24) + 1,
			'dipv4' : (127 << 24) + 1,
			'sport' : 0,
			'dport' : 0,
		}

		if minute not in counter:
			counter[minute] = {}
			for direction in ('sipv4','dipv4','sport','dport'):
				for counter in ('bytes','pckts','flows'):
					# numbers need to be unique, and lower than our traffic
					self._threshold.setdefault(minute,{}).setdefault(direction,{})[counter] = list(range(-1,-self._max_speaker-1,-1))
					self._traffic.setdefault(minute,{}).setdefault(direction,{})[counter] = dict(zip(zip(range(-1,-self._max_speaker-1,-1),[minute,]*self._max_speaker),[default[direction],]*self._max_speaker))

	def purge_minute (self,minute):
		counter = self._counters
		for past in self._threshold.keys()[:-self.period]:
			del counter[past]
			del self._threshold[past]
			del self._traffic[past]

	def ipfix (self,update):
		minute = int(update['epoch'])/60

		with self._traffic_lock:
			self.purge_minute(minute)
			self.make_minute(minute)

			overall = self._overall
			counter = self._counters

			proto = update['proto']
			sipv4 = update['sipv4']
			dipv4 = update['dipv4']
			bytes = update['bytes']
			pckts = update['pckts']
			flows = update['flows']

			counter_total = overall.setdefault('total',{})
			counter_total['bytes'] = counter_total.get('bytes',0) + bytes
			counter_total['pckts'] = counter_total.get('pckts',0) + pckts
			counter_total['flows'] = counter_total.get('flows',0) + flows

			if update['proto'] == 6:  # TCP
				counter_tcp = overall.setdefault('tcp',{})
				counter_tcp['bytes'] = counter_tcp.get('bytes',0) + bytes
				counter_tcp['pckts'] = counter_tcp.get('pckts',0) + pckts
				counter_tcp['flows'] = counter_tcp.get('flows',0) + flows
			elif update['proto'] == 17:  # UDP
				counter_udp = overall.setdefault('udp',{})
				counter_udp['bytes'] = counter_udp.get('bytes',0) + bytes
				counter_udp['pckts'] = counter_udp.get('pckts',0) + pckts
				counter_udp['flows'] = counter_udp.get('flows',0) + flows
			else:
				counter_other = overall.setdefault('other',{})
				counter_other['bytes'] = counter_other.get('bytes',0) + bytes
				counter_other['pckts'] = counter_other.get('pckts',0) + pckts
				counter_other['flows'] = counter_other.get('flows',0) + flows

			#sipv4[time]['sipv4'/'dipv4'/'proto'][sipv4 ip]['pckts'/'bytes'/'flows']
			counter_sipv4 = counter.setdefault(minute,{}).setdefault('sipv4',{}).setdefault(sipv4,{'pckts': 0, 'bytes': 0, 'flows':0})
			counter_sipv4['bytes'] += bytes
			counter_sipv4['pckts'] += pckts
			counter_sipv4['flows'] += flows

			counter_dipv4 = counter.setdefault(minute,{}).setdefault('dipv4',{}).setdefault(dipv4,{'pckts': 0, 'bytes': 0, 'flows':0})
			counter_dipv4['bytes'] += bytes
			counter_dipv4['pckts'] += pckts
			counter_dipv4['flows'] += flows

			counter_proto = counter.setdefault(minute,{}).setdefault('proto',{}).setdefault(proto,{'pckts': 0, 'bytes': 0, 'flows':0})
			counter_proto['bytes'] += bytes
			counter_proto['pckts'] += pckts
			counter_proto['flows'] += flows

			if 'sport' in update:
				counter_sport = counter.setdefault(minute,{}).setdefault('sport',{}).setdefault(update['sport'],{'pckts': 0, 'bytes': 0, 'flows':0})
				counter_sport['bytes'] += bytes
				counter_sport['pckts'] += pckts
				counter_sport['flows'] += flows
			else:
				counter_sport = None

			if 'dport' in update:
				counter_dport = counter.setdefault(minute,{}).setdefault('dport',{}).setdefault(update['dport'],{'pckts': 0, 'bytes': 0, 'flows':0})
				counter_dport['bytes'] += bytes
				counter_dport['pckts'] += pckts
				counter_dport['flows'] += flows
			else:
				counter_dport = None

			for direction,data in (('sipv4',counter_sipv4),('dipv4',counter_dipv4),('sport',counter_sport),('dport',counter_dport)):
				for counter in ('bytes','pckts','flows'):
					traffic = self._traffic[minute][direction][counter]
					maximum = self._threshold[minute][direction][counter]
					ip = update[direction]
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
									maximum = sorted(maximum + [value,])
									break
						# replacing an entry with a new value
						else:
							maximum = sorted(maximum[1:] + [value,])
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

		record = self.monitored()
		if sipv4 in record:
			self.monitor_record(sipv4,sipv4,dipv4,proto,bytes,pckts,flows,update.get('sport',-1),update.get('dport',-1))
		elif dipv4 in record:
			self.monitor_record(dipv4,sipv4,dipv4,proto,bytes,pckts,flows,update.get('sport',-1),update.get('dport',-1))

	def overall (self):
		with self._traffic_lock:
			return deepcopy(self._overall)

	def traffic (self):
		with self._traffic_lock:
			return deepcopy(self._traffic)

	def monitor (self,ipn):
		with self._monitor_lock:
			self._monitor[ipn] = time()

	def monitored (self):
		now = time()
		r = []
		with self._monitor_lock:
			for ipn,back in list(self._monitor.iteritems()):
				# remember seeing the ip for 60 seconds
				if back + self.retain < now:
					del self._monitor[ipn]
					if ipn in self._monitored:
						del self._monitored[ipn]
					continue
				r.append(ipn)
		return r

	def monitor_record (self,ipn,sipv4,dipv4,proto,bytes,pckts,flows,sport,dport):
		# JSON does not let us have list has key :(
		if sport > 0 and dport > 0:
			flow = "%d %d %d %d" % (sipv4,sport,dipv4,dport)
		else:
			flow = "%d %d" % (sipv4,dipv4)

		with self._monitor_lock:
			values = self._monitored.setdefault(ipn,{}).setdefault(proto,{}).setdefault(flow,{})
			values['pckts'] = values.get('pckts',0) + pckts
			values['bytes'] = values.get('bytes',0) + bytes
			values['flows'] = values.get('flows',0) + flows

	def monitor_data (self,ipn):
		with self._monitor_lock:
			return deepcopy(self._monitored.get(ipn,{}))
