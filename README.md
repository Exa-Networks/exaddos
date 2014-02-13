exaddos
=======

Monitor your network for DDOS

ExaDDOS is an application able to gather different data sources to present a real time unified view of your network.

It can gather :
 - SNMP information at your edge
 - IPFIX export from your routers

And present it using a web interface. Our goal is to very quickly integrate it with ExaBGP to allow a "one click" anti-DDOS solution.

The tools is still in development (no release was made yet) and expected to quickly gain features over time.

It is not designed to replace tools like NSFEN which do record and allow complex search on saved record, but to provide an "in flight" view of the flows currently passing through the network.

Our current solution includes:
 - An RRD based solution for interface traffic graphing
 - [AS-STATS](https://neon1.net/as-stats/) to find which peers are our top talkers
 - [NFSEN](http://nfsen.sourceforge.net/) to collect, store and search flows
 - An ExaDDOS like internal solution, to quickly identify which IPs are causing an attack

ExaDDOS is still under development, it is not yet production ready but will slowly get there.
