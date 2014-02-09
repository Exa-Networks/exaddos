"""
configuration.py

Created by Thomas Mangin on 2012-05-01.
Copyright (c) 2012 Exa Networks. All rights reserved.
"""

# encoding: utf-8
"""
configuration.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# XXX: raised exception not caught
# XXX: reloading mid-program not possible
# XXX: validation for path, file, etc not correctly test (ie surely buggy)

import os
import sys
import pwd
import fnmatch

class ConfigurationError (Exception):
	pass

class NoneDict (dict):
	def __getitem__ (self,name):
		return None
nonedict = NoneDict()

class value (object):
	location = os.path.normpath(sys.argv[0]) if sys.argv[0].startswith('/') else os.path.normpath(os.path.join(os.getcwd(),sys.argv[0]))

	@staticmethod
	def integer (_):
		return int(_)

	# router only update SNMP counters every 10 seconds, any faster and all goes wrong
	@staticmethod
	def frequency (_):
		return int(_) if int(_) >= 10 else 10

	@staticmethod
	def lowunquote (_):
		return _.strip().strip('\'"').lower()

	@staticmethod
	def unquote (_):
		return _.strip().strip('\'"')

	@staticmethod
	def quote (_):
		return "'%s'" % str(_)

	@staticmethod
	def nop (_):
		return _

	@staticmethod
	def boolean (_):
		return _.lower() in ('1','yes','on','enable','true')

	@staticmethod
	def methods (_):
		return _.upper().split()

	@staticmethod
	def list (_):
		return "'%s'" % ' '.join(_)

	@staticmethod
	def lower (_):
		return str(_).lower()

	@staticmethod
	def user (_):
		# XXX: incomplete
		try:
			pwd.getpwnam(_)
			# uid = answer[2]
		except KeyError:
			raise TypeError('user %s is not found on this system' % _)
		return _

	@staticmethod
	def folder(path):
		path = os.path.expanduser(value.unquote(path))
		paths = [
			os.path.normpath(os.path.join(os.path.join(os.sep,*os.path.join(value.location.split(os.sep)[:-3])),path)),
			os.path.normpath(os.path.join('/','etc','exaddos','exaddos.conf',path)),
			os.path.normpath(path)
		]
		options = [path for path in paths if os.path.exists(path)]
		if not options: raise TypeError('%s does not exists' % path)
		first = options[0]
		if not first: raise TypeError('%s does not exists' % first)
		return first

	@staticmethod
	def path (path):
		split = sys.argv[0].split('lib/exaddos')
		if len(split) > 1:
			prefix = os.sep.join(split[:1])
			if prefix and path.startswith(prefix):
				path = path[len(prefix):]
		home = os.path.expanduser('~')
		if path.startswith(home):
			return "'~%s'" % path[len(home):]
		return "'%s'" % path

	@staticmethod
	def conf(path):
		first = value.folder(path)
		if not os.path.isfile(first): raise TypeError('%s is not a file' % path)
		return first

	@staticmethod
	def html(path):
		paths = [
			os.path.normpath(path),
			os.path.normpath(os.path.join(os.path.join(os.sep,*os.path.join(value.location.split(os.sep)[:-3])),path)),
			os.path.normpath(os.path.join(os.path.join(os.sep,*os.path.join(value.location.split(os.sep)[:-3])),'data','exaddos','html','index.html')),
			os.path.normpath(os.path.join('/','var','lib','exaddos','html',path)),
		]
		for database in paths:
			if os.path.exists(database):
				return database
		raise TypeError('database could not be found')

	@staticmethod
	def database(path):
		paths = [
			os.path.normpath(path),
			os.path.normpath(os.path.join(os.path.join(os.sep,*os.path.join(value.location.split(os.sep)[:-3])),path)),
			os.path.normpath(os.path.join(os.path.join(os.sep,*os.path.join(value.location.split(os.sep)[:-3])),'data','exaddos','db','exaddos.sqlite3')),
			os.path.normpath(os.path.join('/','var','lib','exaddos',path)),
		]
		for database in paths:
			if os.path.exists(database):
				return database
		raise TypeError('database could not be found')

	@staticmethod
	def exe (path):
		first = value.conf(path)
		if not os.access(first, os.X_OK): raise TypeError('%s is not an executable' % first)
		return first

	@staticmethod
	def syslog (path):
		path = value.unquote(path)
		if path in ('stdout','stderr'):
			return path
		if path.startswith('host:'):
			return path
		return path

defaults = {
	# 'database' : {
	# 	'location'             : (value.database,value.path,  'exaddos.sqlite3',     'the sqlite3 database location')
	# },
	'daemon' : {
#		'pidfile'              : (value.unquote,value.quote,     '',               'where to save the pid if we manage it'),
		'user'                 : (value.user,value.quote,        'nobody',         'user to run as'),
#		'daemonize'            : (value.boolean,value.lower,     'false',          'should we run in the background'),
	},

	'http' : {
		'host'                 : (value.unquote,value.quote,     '127.0.0.1',      'the address the web server listens on'),
		'port'                 : (value.integer,value.nop,       '39200',          'port the web server listens on'),
	},

	'location' : {
		'html'                 : (value.html,value.quote,        'index.html',     'the /index.html page'),
	},

	'profile' : {
		'enable'               : (value.boolean,value.lower,     'false',          'enable profiling'),
		'destination'          : (value.syslog,value.quote,      'stdout',         'save profiling to file (instead of to the screen on exit)'),
	},

	'[A-Z]*' : {
		'router'               : (value.unquote,value.quote,     '127.0.0.1',      ''),
		'snmp_version'         : (value.integer,value.nop,       '2',              'only version 2 supported'),
		'snmp_password'        : (value.unquote,value.quote,     'public',         'your passwords are secure aren\'t they'),
		'snmp_frequency'       : (value.frequency,value.nop,     '10',             'snmp pulling frequency (minimum 10 seconds)'),
		'snmp_index_port'      : (value.integer,value.nop,       '0',              'physical interface SNMP interface index'),
		'snmp_index_vlan'      : (value.integer,value.nop,       '0',              'vlan/ae/other SNMP interface index (or physical if not defined)'),
		'threshold_bandwidth'  : (value.integer,value.nop,       '0',              'threshold for abnormal unicast traffic (bits)'),
		'threshold_unicast'    : (value.integer,value.nop,       '0',              'threshold for abnormal unicast traffic (pps)'),
		'threshold_notunicast' : (value.integer,value.nop,       '0',              'threshold for abnormal non unicast (icmp mostly) traffic (pps)'),
	},

	# Here for internal use
	'internal' : {
		'name'         : (value.nop,value.nop,           'ExaDDOS',        'name'),
		'version'      : (value.nop,value.nop,           '0.1.0',          'version'),
	},

	# Here for internal use
	'debug' : {
		'pdb'         : (value.boolean,value.lower,'false','command line option --pdb'),
		'memory'      : (value.boolean,value.lower,'false','command line option --memory'),
	},
}

import ConfigParser

class Store (dict):
	def __getitem__ (self,key):
		return dict.__getitem__(self,key.replace('_','-'))
	def __setitem__ (self,key,value):
		return dict.__setitem__(self,key.replace('_','-'),value)
	def __getattr__ (self,key):
		return dict.__getitem__(self,key.replace('_','-'))
	def __setattr__ (self,key,value):
		return dict.__setitem__(self,key.replace('_','-'),value)


def _configuration (conf):
	location = os.path.join(os.sep,*os.path.join(value.location.split(os.sep)))
	while location:
		location, directory = os.path.split(location)
		if directory == 'lib':
			break

	_conf_paths = []
	if conf:
		_conf_paths.append(os.path.abspath(os.path.normpath(conf)))
	if location:
		_conf_paths.append(os.path.normpath(os.path.join(location,'etc','exaddos','exaddos.conf')))
	_conf_paths.append(os.path.normpath(os.path.join('/','etc','exaddos','exaddos.conf')))

	try:
		ini_file = [path for path in _conf_paths if os.path.exists(path)][0]
	except IndexError:
		ini_file = None

	if not ini_file:
		raise ConfigurationError('could not find exaddos.conf file')

	ini = ConfigParser.ConfigParser()
	ini.read(ini_file)

	templates = {}
	for section in defaults:
		for wildcard in ('*','?','['):
			if wildcard in section:
				templates[section] = defaults[section]

	for section in templates:
		del defaults[section]

	for section in ini.sections():
		for template in templates:
			search = 'exaddos.%s' % template
			if fnmatch.fnmatch(section,search):
				defaults[section[len('exaddos.'):]] = templates[template]

	configuration = Store()

	for section in defaults:
		default = defaults[section]

		for option in default:
			convert = default[option][0]
			try:
				proxy_section = 'exaddos.%s' % section
				env_name = '%s.%s' % (proxy_section,option)
				conf = value.unquote(os.environ.get(env_name,'')) \
				    or value.unquote(os.environ.get(env_name.replace('.','_'),'')) \
				    or value.unquote(ini.get(proxy_section,option,nonedict)) \
				    or default[option][2]
			except (ConfigParser.NoSectionError,ConfigParser.NoOptionError):
				conf = default[option][2]
			try:
				configuration.setdefault(section,Store())[option] = convert(conf)
			except TypeError:
				raise ConfigurationError('invalid value for %s.%s : %s' % (section,option,conf))

	return configuration

__configuration = None

def load (conf=None):
	global __configuration
	if __configuration:
		return __configuration
	if conf is None:
		raise RuntimeError('You can not have an import using load() before main() initialised it')
	__configuration = _configuration(conf)
	return __configuration

def default ():
	for section in sorted(defaults):
		if section in ('internal','debug'):
			continue
		for option in sorted(defaults[section]):
			values = defaults[section][option]
			default = "'%s'" % values[2] if values[1] in (value.list,value.path,value.quote,value.syslog) else values[2]
			yield 'exaddos.%s.%s %s: %s. default (%s)' % (section,option,' '*(20-len(section)-len(option)),values[3],default)

def ini (diff=False):
	for section in sorted(__configuration):
		if section in ('internal','debug'):
			continue
		header = '\n[exaddos.%s]' % section
		for k in sorted(__configuration[section]):
			v = __configuration[section][k]
			if diff and defaults[section][k][0](defaults[section][k][2]) == v:
				continue
			if header:
				print header
				header = ''
			print '%s = %s' % (k,defaults[section][k][1](v))

def env (diff=False):
	print
	for section,values in __configuration.items():
		if section in ('internal','debug'):
			continue
		for k,v in values.items():
			if diff and defaults[section][k][0](defaults[section][k][2]) == v:
				continue
			if defaults[section][k][1] == value.quote:
				print "exaddos.%s.%s='%s'" % (section,k,v)
				continue
			print "exaddos.%s.%s=%s" % (section,k,defaults[section][k][1](v))
