# encoding: utf-8
"""
warning.py

Created by Thomas Mangin on 2014-02-07.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

def unicast (information,interface):
	return information['ifHCInUcastPkts'] > interface.threshold_unicast

def notunicast (information,interface):
	return information['ifInNUcastPkts'] > interface.threshold_notunicast

def bw (information,interface):
	return information['ifHCInOctets'] > interface.threshold_bandwidth
