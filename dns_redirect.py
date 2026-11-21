import socket
from dnslib import DNSRecord, DNSHeader, RR, A, QTYPE

LAPTOP_IP = "192.168.2.22"
UPSTREAM_DNS = ("1.1.1.1", 53)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 53))
print(f"[*] DNS Interceptor running on {LAPTOP_IP}:53 (hijacking *naxclow*)...")

while True:
    try:
        data, addr = sock.recvfrom(4096)
        d = DNSRecord.parse(data)
        qname = str(d.q.qname).lower()
        if "naxclow" in qname:
            print(f"[+] HIJACKED Camera DNS query from {addr[0]}: {qname} -> {LAPTOP_IP}")
            reply = DNSRecord(DNSHeader(id=d.header.id, qr=1, aa=1, ra=1), q=d.q)
            reply.add_answer(RR(d.q.qname, QTYPE.A, rdata=A(LAPTOP_IP), ttl=60))
            sock.sendto(reply.pack(), addr)
        else:
            up = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            up.settimeout(2)
            up.sendto(data, UPSTREAM_DNS)
            resp, _ = up.recvfrom(4096)
            sock.sendto(resp, addr)
            up.close()
    except Exception as e:
        pass
