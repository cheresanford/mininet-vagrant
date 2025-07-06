#!/bin/bash
# Experimento com TCP BBR

time=90
bwnet=1.5          # Mb/s (link gargalo)
delay=5ms          # RTT total 20 ms  ->  10 ms ida (5 ms por enlace)
iperf_port=5001    # (não muda nada, só mantenho a variável)

for qsize in 20 100; do
    dir=bbr-q$qsize          # pasta onde tudo será salvo

    # 1) Executa o experimento
    python3 bufferbloat.py \
        --bw-net $bwnet \
        --delay ${delay%ms} \
        --dir $dir \
        --time $time \
        --maxq $qsize \
        --cong bbr            # ← muda o algoritmo de controle

    # 2) Gera os gráficos
    echo "Gerando gráficos..."
    python3 plot_queue.py -f $dir/q.txt   -o bbr-buffer-q$qsize.png
    python3 plot_ping.py  -f $dir/ping.txt -o bbr-rtt-q$qsize.png
done
