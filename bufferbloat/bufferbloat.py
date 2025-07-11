from mininet.topo import Topo
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.log import lg, info
from mininet.util import dumpNodeConnections
from mininet.cli import CLI

from subprocess import Popen, PIPE
from time import sleep, time
from multiprocessing import Process
from argparse import ArgumentParser

import statistics
from monitor import monitor_qlen

import sys
import os
import math

parser = ArgumentParser(description="Bufferbloat tests")
parser.add_argument('--bw-host', '-B',
                    type=float,
                    help="Bandwidth of host links (Mb/s)",
                    default=1000)

parser.add_argument('--bw-net', '-b',
                    type=float,
                    help="Bandwidth of bottleneck (network) link (Mb/s)",
                    required=True)

parser.add_argument('--delay',
                    type=float,
                    help="Link propagation delay (ms)",
                    required=True)

parser.add_argument('--dir', '-d',
                    help="Directory to store outputs",
                    required=True)

parser.add_argument('--time', '-t',
                    help="Duration (sec) to run the experiment",
                    type=int,
                    default=10)

parser.add_argument('--maxq',
                    type=int,
                    help="Max buffer size of network interface in packets",
                    default=100)

# Linux uses CUBIC-TCP by default that doesn't have the usual sawtooth
# behaviour.  For those who are curious, invoke this script with
# --cong cubic and see what happens...
# sysctl -a | grep cong should list some interesting parameters.
parser.add_argument('--cong',
                    help="Congestion control algorithm to use",
                    default="reno")

# Expt parameters
args = parser.parse_args()

class BBTopo(Topo):
    "Simple topology for bufferbloat experiment."

    def build(self, n=2):
        # TODO: create two hosts

        # TODO: Add links with appropriate characteristics
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s0 = self.addSwitch('s0')

        #  Host ↔ switch: altíssima banda (bw-host) e atraso quase nulo
        self.addLink(h1, s0,
                     bw=args.bw_host,
                     delay='0.1ms',
                     max_queue_size=1000,
                     use_htb=True)

        #  Gargalo: switch ↔ host 2
        self.addLink(s0, h2,
                     bw=args.bw_net,
                     delay='{}ms'.format(args.delay),
                     max_queue_size=args.maxq,
                     use_htb=True)
        

# Simple wrappers around monitoring utilities.  You are welcome to
# contribute neatly written (using classes) monitoring scripts for
# Mininet!

def fetch_page(hclient, hserver, log_file):
    """Baixa index.html 3 vezes e registra tempos"""
    t_list = []
    for _ in range(3):
        t = hclient.cmd(
            "curl -o /dev/null -s -w '%{time_total}\\n' http://%s/index.html" %
            hserver.IP())
        t_list.append(float(t))
        with open(log_file, 'a') as f:
            f.write(t)
    return t_list


def start_iperf(net):
    h1 = net.get('h1')
    h2 = net.get('h2')
    print("Starting iperf server...")
    # For those who are curious about the -w 16m parameter, it ensures
    # that the TCP flow is not receiver window limited.  If it is,
    # there is a chance that the router buffer may not get filled up.
    server = h2.popen("iperf -s -w 16m")

    # TODO: Start the iperf client on h1.  Ensure that you create a
    # long lived TCP flow.
    client = h1.popen("iperf -c {} -t {} -i 1"
                      .format(h2.IP(), args.time))
    return server, client

def start_qmon(iface, interval_sec=0.1, outfile="q.txt"):
    monitor = Process(target=monitor_qlen,
                      args=(iface, interval_sec, outfile))
    monitor.start()
    return monitor

def start_ping(net):
    # TODO: Start a ping train from h1 to h2 (or h2 to h1, does it
    # matter?)  Measure RTTs every 0.1 second.  Read the ping man page
    # to see how to do this.

    # Hint: Use host.popen(cmd, shell=True).  If you pass shell=True
    # to popen, you can redirect cmd's output using shell syntax.
    # i.e. ping ... > /path/to/ping.
    h1, h2 = net.get('h1', 'h2')
    ping = h1.popen(f'ping {h2.IP()} -i 0.1 -D    > {args.dir}/ping.txt',
                shell=True)
    return ping

def start_webserver(net):
    h1 = net.get('h1')
    proc = h1.popen("python webserver.py", shell=True)
    sleep(1)
    return [proc]

def bufferbloat():
    if not os.path.exists(args.dir):
        os.makedirs(args.dir)
    os.system("sysctl -w net.ipv4.tcp_congestion_control=%s" % args.cong)
    topo = BBTopo()
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)
    net.start()
    # This dumps the topology and how nodes are interconnected through
    # links.
    dumpNodeConnections(net.hosts)
    # This performs a basic all pairs ping test.
    net.pingAll()

    # TODO: Start monitoring the queue sizes.  Since the switch I
    # created is "s0", I monitor one of the interfaces.  Which
    # interface?  The interface numbering starts with 1 and increases.
    # Depending on the order you add links to your network, this
    # number may be 1 or 2.  Ensure you use the correct number.
    qmon = start_qmon(iface='s0-eth2',
                      outfile='%s/q.txt' % (args.dir))

    # TODO: Start iperf, webservers, etc.
    start_iperf(net)
    start_ping(net)
    start_webserver(net)

    # TODO: measure the time it takes to complete webpage transfer
    # from h1 to h2 (say) 3 times.  Hint: check what the following
    # command does: curl -o /dev/null -s -w %{time_total} google.com
    # Now use the curl command to fetch webpage from the webserver you
    # spawned on host h1 (not from google!)
    # Hint: Verify the url by running your curl command without the
    # flags. The html webpage should be returned as the response.

    # Hint: have a separate function to do this and you may find the
    # loop below useful.
    h1, h2 = net.get('h1', 'h2')          # hosts já criados
    fetch_log = os.path.join(args.dir, 'fetch.txt')

    # garante que o arquivo exista zerado
    open(fetch_log, 'w').close()
    start_time = time()
    while True:
        # mede 3 downloads consecutivos da página index.html
        for _ in range(3):
            fetch_time = h2.cmd(
                "curl -o /dev/null -s -w '%%{time_total}\\n' http://%s/index.html"
                % h1.IP()
            )
            # grava resultado no arquivo de log
            with open(fetch_log, 'a') as f:
                f.write(fetch_time)

        sleep(5)                          # espera 5 s antes do próximo trio
        delta = time() - start_time
        if delta > args.time:             # tempo total do experimento acabou?
            break
        print(f"{args.time - delta:.1f}s left…")

    # TODO: compute average (and standard deviation) of the fetch
    # times.  You don't need to plot them.  Just note it in your
    # README and explain.
    with open(fetch_log) as f:
        times = [float(line.strip()) for line in f if line.strip()]

    avg = statistics.mean(times)
    std = statistics.stdev(times) if len(times) > 1 else 0
    print(f"Average fetch time: {avg:.3f}s ± {std:.3f}s")

    with open(os.path.join(args.dir, 'fetch_stats.txt'), 'w') as fstats:
        fstats.write(f"{avg},{std}\n")

    # Hint: The command below invokes a CLI which you can use to
    # debug.  It allows you to run arbitrary commands inside your
    # emulated hosts h1 and h2.
    # CLI(net)
    CLI(net)
    qmon.terminate()
    net.stop()
    # Ensure that all processes you create within Mininet are killed.
    # Sometimes they require manual killing.
    Popen("pgrep -f webserver.py | xargs kill -9", shell=True).wait()

if __name__ == "__main__":
    bufferbloat()
