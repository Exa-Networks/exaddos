"""
application.py

Created by Thomas Mangin on 2014-02-06.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

import os
import sys
import pwd

import socket
import errno

from .log import log,err,silence
from exaddos import reactor

def __exit(memory,code):
	if memory:
		from exaddos.leak import objgraph
		print "memory utilisation"
		print
		print objgraph.show_most_common_types(limit=20)
		print
		print
		print "generating memory utilisation graph"
		print
		obj = objgraph.by_type('run')
		objgraph.show_backrefs([obj], max_depth=10)
	sys.exit(code)


def __drop_privileges (user):
	"""returns true if we are left with insecure privileges"""
	try:
		user = pwd.getpwnam(user)
		nuid = int(user.pw_uid)
		ngid = int(user.pw_gid)
	except KeyError:
		return False

	uid = os.getuid()
	gid = os.getgid()

	# not sure you can change your gid if you do not have a pid of zero
	try:
		# we must change the GID first otherwise it may fail after change UID
		if not gid:
			os.setgid(ngid)
		if not uid:
			os.setuid(nuid)

		cuid = os.getuid()
		ceid = os.geteuid()
		cgid = os.getgid()

		if cuid < 0:
			cuid = (1<<32) + cuid

		if cgid < 0:
			cgid = (1<<32) + cgid

		if ceid < 0:
			ceid = (1<<32) + ceid

		if nuid != cuid or nuid != ceid or ngid != cgid:
			return False

	except OSError:
		return False

	return True

def drop_privileges (configuration):
	# os.name can be ['posix', 'nt', 'os2', 'ce', 'java', 'riscos']
	if os.name not in ['posix',]:
		return True

	if os.getuid() != 0:
		err('not running as root, not changing UID')
		return True

	users = [configuration.daemon.user,'nobody']

	for user in users:
		if __drop_privileges(user):
			return True
	return False

def daemonise (daemonize):
	if not daemonize:
		return

	def fork_exit ():
		try:
			pid = os.fork()
			if pid > 0:
				os._exit(0)
		except OSError, e:
			err('Can not fork, errno %d : %s' % (e.errno,e.strerror))

	def mute ():
		# closing more would close the log file too if open
		maxfd = 3

		for fd in range(0, maxfd):
			try:
				os.close(fd)
			except OSError:
				pass
		os.open("/dev/null", os.O_RDWR)
		os.dup2(0, 1)
		os.dup2(0, 2)

	def is_socket (fd):
		try:
			s = socket.fromfd(fd, socket.AF_INET, socket.SOCK_RAW)
		except ValueError,e:
			# The file descriptor is closed
			return False
		try:
			s.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
		except socket.error, e:
			# It is look like one but it is not a socket ...
			if e.args[0] == errno.ENOTSOCK:
				return False
		return True

	# do not detach if we are already supervised or run by init like process
	if is_socket(sys.__stdin__.fileno()) or os.getppid() == 1:
		return

	fork_exit()
	os.setsid()
	fork_exit()
	mute()
	silence()


def help ():
	sys.stdout.write('usage:\n exaddos [options]\n')
	sys.stdout.write('\n')
	sys.stdout.write('  -h, --help      : this help\n')
	sys.stdout.write('  -c, --conf-file : configuration file to use (ini format)\n')
	sys.stdout.write('  -i, --ini       : display the configuration using the ini format\n')
	sys.stdout.write('  -e, --env       : display the configuration using the env format\n')
	sys.stdout.write(' -di, --diff-ini  : display non-default configurations values using the ini format\n')
	sys.stdout.write(' -de, --diff-env  : display non-default configurations values using the env format\n')
	sys.stdout.write('  -d, --debug     : shortcut to turn on all subsystems debugging to LOG_DEBUG\n')
	sys.stdout.write('  -p, --pdb       : start the python debugger on serious logging and on SIGTERM\n')
	sys.stdout.write('  -m, --memory    : display memory usage information on exit\n')

	sys.stdout.write('\n')
	sys.stdout.write('iEnum will automatically look for its configuration file (in windows ini format)\n')
	sys.stdout.write(' - in the etc/exaddos folder located within the extracted tar.gz \n')
	sys.stdout.write(' - in /etc/exaddos/exaddos.conf\n')
	sys.stdout.write('\n')
	sys.stdout.write('Every configuration value has a sensible built-in default\n')
	sys.stdout.write('\n')
	sys.stdout.write('Individual configuration options can be set using environment variables, such as :\n')
	sys.stdout.write('   > env exaddos.http.port=39200 ./sbin/exaddos\n')
	sys.stdout.write('or > env exaddos_http_port=39200 ./sbin/exaddos\n')
	sys.stdout.write('or > export exaddos_http_port=39200; ./sbin/exaddos\n')
	sys.stdout.write('\n')
	sys.stdout.write('Multiple environment values can be set\n')
	sys.stdout.write('and the order of preference is :\n')
	sys.stdout.write(' - 1 : command line env value using dot separated notation\n')
	sys.stdout.write(' - 2 : exported value from the shell using dot separated notation\n')
	sys.stdout.write(' - 3 : command line env value using underscore separated notation\n')
	sys.stdout.write(' - 4 : exported value from the shell using underscore separated notation\n')
	sys.stdout.write(' - 5 : the value in the ini configuration file\n')
	sys.stdout.write('\n')
	sys.stdout.write('Valid configuration options are :\n')
	sys.stdout.write('\n')
	for line in default():
			sys.stdout.write(' - %s\n' % line)
	sys.stdout.write('\n')

def version_warning ():
	sys.stderr.write('This version of python is not supported\n')

if __name__ == '__main__':
	main = int(sys.version[0])
	secondary = int(sys.version[2])

	if main != 2 or secondary < 4:
		sys.exit('This program can not work (is not tested) with your python version (< 2.4 or >= 3.0)')

	if main == 2 and secondary == 4:
		version_warning()

	try:
		from pysnmp.smi import builder
		builder.MibBuilder().loadModules('SNMPv2-MIB', 'IF-MIB')
	except:
		sys.exit('This program requires python netsnmp\n> pip install pysnmp\n>pip install pysnmp_mibs')

	from exaddos.configuration import ConfigurationError,load,ini,env,default

	next = ''
	arguments = {
		'configuration' : '',
	}

	for arg in sys.argv[1:]:
		if next:
			arguments[next] = arg
			next = ''
			continue
		if arg in ['-c','--conf-file']:
			next = 'configuration'

	for arg in sys.argv[1:]:
		if arg in ['--',]:
			break
		if arg in ['-h','--help']:
			help()
			sys.exit(0)

	try:
		configuration = load(arguments['configuration'])
	except ConfigurationError,e:
		err('configuration issue, %s' % str(e))
		sys.exit(1)

	for arg in sys.argv[1:]:
		if arg in ['--',]:
			break
		if arg in ['-h','--help']:
			help()
			sys.exit(0)
		if arg in ['-i','--ini']:
			ini()
			sys.exit(0)
		if arg in ['-e','--env']:
			env()
			sys.exit(0)
		if arg in ['-di','--diff-ini']:
			ini(True)
			sys.exit(0)
		if arg in ['-de','--diff-env']:
			env(True)
			sys.exit(0)
		if arg in ['-p','--pdb']:
			# The following may fail on old version of python (but is required for debug.py)
			os.environ['PDB'] = 'true'
			configuration.debug.pdb = True
		if arg in ['-D']:
			configuration.daemon.daemonize = True
		if arg in ['-m','--memory']:
			configuration.debug.memory = True

	# check the database is well only 400 by the user we use
	# start web server :)

	reactor.setup(configuration)

	if not drop_privileges(configuration):
		err('could not drop privileges')
		__exit(configuration.debug.memory,0)

	daemonise(configuration.daemon.daemonize)

	if not configuration.profile.enable:
		try:
			reactor.run()
		except socket.error,e:
			# XXXX: Look at ExaBGP code fore better handling
			if e.errno == errno.EADDRINUSE:
				err('can not bind to %s:%d (port already/still in use)' % (configuration.http.host, configuration.http.port))
			if e.errno == errno.EADDRNOTAVAIL:
				err('can not bind to %s:%d (IP unavailable)' % (configuration.http.host, configuration.http.port))
		__exit(configuration.debug.memory,0)

	try:
		import cProfile as profile
	except:
		try:
			import profile
		except:
			err('could not perform profiling')
			class profile (object):
				@staticmethod
				def run (function):
					eval(function)

	profile.run('reactor.run()')
	__exit(configuration.debug.memory,0)
