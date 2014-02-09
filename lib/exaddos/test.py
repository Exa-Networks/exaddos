from pysnmp.smi import builder

mibBuilder = builder.MibBuilder().loadModules('SNMPv2-MIB', 'IF-MIB')

ifHCInOctets = mibBuilder.importSymbols('IF-MIB', 'ifHCInOctets')

interface = ifHCInOctets[0].getName() + (595,)

from pysnmp.entity.rfc3413.oneliner import cmdgen


#    cmdgen.CommunityData('test-agent', 'public', 0),
#    cmdgen.UsmUserData('test-user', 'authkey1', 'privkey1'),
errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(
	cmdgen.CommunityData('test-agent', 'EXA-SNMP-NETWORKS-RO'),
	cmdgen.UdpTransportTarget(('82.219.0.24', 161)),
	interface
)

if (errorStatus,errorIndex) != (0,0):
	print "errorIndication",errorIndication
	print "errorIndex",errorIndex
	print "errorStatus",errorStatus
else:
	for k,v in varBinds:
		print k,':',v
