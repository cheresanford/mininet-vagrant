#!/usr/bin/env python3
"""
Experimento de competição Reno × BBR em Mininet usando iperf 2 (CSV).
Saída: um .csv por fluxo contendo throughput por segundo.
"""

import argparse, os, time, shlex
from mininet.net     import Mininet
from mininet.link    import TCLink
from mininet.node    import OVSSwitch
from mininet.log     import setLogLevel

# ---------- argumentos de linha de comando ----------
parser = argparse.ArgumentParser()
parser.add_argument('--bw',     type=float, required=True, help='bottleneck Mbps')
parser.add_argument('--delay',               required=True, help='bottleneck delay (ex.: 50ms)')
parser.add_argument('--time',   type=int,   required=True, help='duração do experimento (s)')
parser.add_argument('--reno',   type=int,   required=True, help='# fluxos Reno')
parser.add_argument('--bbr',    type=int,   required=True, help='# fluxos BBR')
parser.add_argument('--output',              required=True, help='diretório de saída')
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)
setLogLevel('info')

# ---------- consts ----------
BASE_RENO = 5001
BASE_BBR  = 6001

# ---------- cria rede ----------
net = Mininet(controller=None,         # <<< sem controlador
              switch=OVSSwitch,
              link=TCLink,
              autoStaticArp=True,
              build=False)

hR = net.addHost('hR')   # envia Reno
hB = net.addHost('hB')   # envia BBR
hS = net.addHost('hS')   # receptor
s0 = net.addSwitch('s0', failMode='standalone')   # L2 bridge

for h in (hR, hB):
    net.addLink(h, s0, bw=1000, delay='0.1ms')

net.addLink(s0, hS, bw=args.bw, delay=args.delay)
net.build(); net.start()

# ---------- força CCA ----------
hR.cmd('sysctl -w net.ipv4.tcp_congestion_control=reno > /dev/null')
hB.cmd('sysctl -w net.ipv4.tcp_congestion_control=bbr  > /dev/null')

# ---------- teste de conectividade ----------
ping_ok = hR.cmd(f'ping -c1 -W1 {hS.IP()}').find('1 packets transmitted, 1 received') > -1
if not ping_ok:
    raise RuntimeError('ping falhou – verifique links/endereços')

# ---------- servidores iperf (em hS) ----------
for i in range(args.reno):
    hS.popen(f'iperf -s -p {BASE_RENO+i} -f m', stdout=open(os.devnull,'w'))
for i in range(args.bbr):
    hS.popen(f'iperf -s -p {BASE_BBR+i}  -f m', stdout=open(os.devnull,'w'))

time.sleep(1.0)      # garante servidores de pé

# ---------- clientes ----------
clients = []

def launch(host, port, tag, idx):
    csv = f'{args.output}/{tag}_{idx}.csv'
    err = f'{args.output}/{tag}_{idx}.err'
    cmd = f'iperf -c {hS.IP()} -p {port} -t {args.time} -y C'
    p = host.popen(shlex.split(cmd),
                   stdout=open(csv,'w'),
                   stderr=open(err,'w'))
    clients.append(p)

for i in range(args.reno):
    launch(hR, BASE_RENO+i, 'reno', i)
for i in range(args.bbr):
    launch(hB, BASE_BBR+i,  'bbr',  i)

# ---------- espera terminar ----------
for p in clients:
    p.wait()

hS.cmd('killall -q iperf')
net.stop()
print('[OK] CSV gerados em', args.output)
