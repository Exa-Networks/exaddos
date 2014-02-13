# encoding: utf-8
"""
ipfix.py

Created by Thomas Mangin on 2014-02-09.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

import struct

# http://www.iana.org/assignments/ipfix/ipfix.xhtml

class TEMPLATE (object):
	octetDeltaCount             = 1
	packetDeltaCount            = 2
	deltaFlowCount              = 3
	protocolIdentifier          = 4
	ipClassOfService            = 5
	tcpControlBits              = 6
	sourceTransportPort         = 7
	sourceIPv4Address           = 8
	sourceIPv4PrefixLength      = 9
	ingressInterface            = 10
	destinationTransportPort    = 11
	destinationIPv4Address      = 12
	destinationIPv4PrefixLength = 13
	egressInterface             = 14
	ipNextHopIPv4Address        = 15
	bgpSourceAsNumber           = 16
	bgpDestinationAsNumber      = 17
	bgpNextHopIPv4Address       = 18
	# ....
	ipv6flowlabel               = 31


class PROTOCOL:
	ICMP = 1
	TCP  = 6
	UDP  = 17


CONVERT = {
	(TEMPLATE.octetDeltaCount,1)  : '>B',
	(TEMPLATE.octetDeltaCount,2)  : '>H',
	(TEMPLATE.octetDeltaCount,4)  : '>I',
	(TEMPLATE.octetDeltaCount,8)  : '>Q',

	(TEMPLATE.packetDeltaCount,1)  : '>B',
	(TEMPLATE.packetDeltaCount,2)  : '>H',
	(TEMPLATE.packetDeltaCount,4)  : '>I',
	(TEMPLATE.packetDeltaCount,8)  : '>Q',

	(TEMPLATE.protocolIdentifier,1)  : '>B',
	(TEMPLATE.protocolIdentifier,2)  : '>H',
	(TEMPLATE.protocolIdentifier,4)  : '>I',
	(TEMPLATE.protocolIdentifier,8)  : '>Q',

	(TEMPLATE.sourceIPv4Address,1)  : '>B',
	(TEMPLATE.sourceIPv4Address,2)  : '>H',
	(TEMPLATE.sourceIPv4Address,4)  : '>I',
	(TEMPLATE.sourceIPv4Address,8)  : '>Q',

	(TEMPLATE.destinationIPv4Address,1)  : '>B',
	(TEMPLATE.destinationIPv4Address,2)  : '>H',
	(TEMPLATE.destinationIPv4Address,4)  : '>I',
	(TEMPLATE.destinationIPv4Address,8)  : '>Q',

}

NAME = {
	TEMPLATE.protocolIdentifier     : 'proto',
	TEMPLATE.sourceIPv4Address      : 'sipv4',
	TEMPLATE.destinationIPv4Address : 'dipv4',
	TEMPLATE.octetDeltaCount        : 'bytes',
	TEMPLATE.packetDeltaCount       : 'pckts',
}

class IPFIX (object):
	care = [
		TEMPLATE.protocolIdentifier,
		TEMPLATE.sourceIPv4Address,
		TEMPLATE.destinationIPv4Address,
		TEMPLATE.octetDeltaCount,
		TEMPLATE.packetDeltaCount,
	]

	nice = [
		TEMPLATE.destinationTransportPort,
	]

	def __init__ (self,callback):
		self.template = {}
		self.callback = callback

# The format of the IPFIX Message Header
#    0                   1                   2                   3
#    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |       Version Number          |            Length             |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                           Export Time                         |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                       Sequence Number                         |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                    Observation Domain ID                      |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

	def read (self,data):
		version, length, epoch, sequence, domain = struct.unpack(">HHIII", data[:16])

		if version != 10:
			return

		if length > len(data):
			return

		return self.read_set(epoch,data[16:])

# SET Header
#  0                   1                   2                   3
#  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# |          Set ID               |          Length               |
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

	def read_set (self,epoch,data):
		if not data:
			return

		ID, length = struct.unpack(">HH", data[:4])

		if ID >= 256:
			return self.read_data(ID,epoch,data[4:])
		if ID == 2:
			return self.read_template(epoch,data[4:])
		if ID == 3:
			return self.read_option_template(epoch,data[4:])

		# ID 0 .. 1   : not used historical reasons
		# ID 4 .. 255 : reserved

	# Template Record Header

	#   0                   1                   2                   3
	#   0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
	#  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#  |      Template ID (> 255)      |         Field Count           |
	#  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

	# The Field Specifier format is shown in Figure G.

	#  0                   1                   2                   3
	#  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
	#  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#  |E|  Information Element ident. |        Field Length           |
	#  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#  |                      Enterprise Number                        |
	#  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

	def read_template (self,epoch,data):
		template, number = struct.unpack(">HH", data[:4])

		# we do not give a damn about enterprise data
		if template & 0b1000000000000000:  # 1 << 15
			#enterprise = struct.unpack(">I",data[4:8])
			return self.read_set(epoch,data[8:])

		# deleting known template
		if number == 0:
			if template in self.template:
				del self.template[template]
			return self.read_set(epoch,data[4:])

		format = {}
		offset = 0

		for index in range(number):
			what, size = struct.unpack(">HH", data[4+(index*4):4+(index*4)+4])
			if what in self.care:
				format[what] = (offset,size)
			offset += size

		# the template has what we care about :-)
		if len(format) == len(self.care):
			self.template[template] = format

		return self.read_set(epoch,data[4 + (number*4):])

# 0                   1                   2                   3
#  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# |         Template ID (> 255)   |         Field Count           |
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# |      Scope Field Count        |
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

# +--------------------------------------------------+
# | Options Template Record Header                   |
# +--------------------------------------------------+
# | Field Specifier                                  |
# +--------------------------------------------------+
# | Field Specifier                                  |
# +--------------------------------------------------+
#  ...
# +--------------------------------------------------+
# | Field Specifier                                  |
# +--------------------------------------------------+

	def read_option_template (self,epoch,data):
		template, number, scope = struct.unpack(">HHH", data[:6])

		# as we do not really care :-)
		# Juniper return number*4 + scope*2 !
		return self.read_set(epoch,data[6+(number*4)+(scope*2):])

		# # deleting known template
		# if number == 0:
		# 	if template in self.template:
		# 		del self.template[template]
		# 	return self.read_set(epoch,data[4:])

		# # invalid data
		# if scope == 0 or scope > number:
		# 	return

		# # process scope fields
		# for _ in range (scope):
		# 	what, size = struct.unpack(">HH", data[:4])
		# 	pass

		# # process "normal" options fields
		# for _ in range (number-scope):
		# 	what, size = struct.unpack(">HH", data[:4])
		# 	pass

		# #return self.read_set(epoch,data[6+(number*4):])

	def read_data (self,setid,epoch,data):
		# unknown template, ignore it !
		if setid not in self.template:
			return

		extracted = {'epoch':epoch,'flows':1}
		format = self.template[setid]

		for what in format:
			offset,size = format[what]
			extracted[NAME[what]], = struct.unpack(CONVERT[(what,size)],data[offset:offset+size])

		self.callback(extracted)
