AF_INET = 2
def interfaces(): return ['eth0']
def gateways(): return {'default': {2: ('192.168.2.22', 'eth0')}}
def ifaddresses(iface): return {2: [{'addr': '192.168.2.22'}]}
