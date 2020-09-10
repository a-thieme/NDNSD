import time
import sys

from mininet.log import setLogLevel, info

from minindn.minindn import Minindn
from minindn.util import MiniNDNCLI
from minindn.apps.app_manager import AppManager
from minindn.apps.nfd import Nfd
from minindn.helpers.nfdc import Nfdc
from subprocess import Popen, PIPE
import os
from minindn.apps.nlsr import Nlsr
from minindn.helpers.ndn_routing_helper import NdnRoutingHelper
import subprocess

import time
from random import randrange

numberOfUpdates = 300
jitter = 50

def cleanUp():
    pass

def registerRouteToAllNeighbors(ndn, host, syncPrefix):
    for node in ndn.net.hosts:
        for neighbor in node.connectionsTo(host):
            ip = node.IP(neighbor[0])
            Nfdc.createFace(host, ip)
            Nfdc.registerRoute(host, syncPrefix, ip)

class NDNSDExperiment():

  def __init__(self, arg, producers, consumers):
    self.ndn = Minindn()
    self.args = arg
    self.producers = producers
    self.consumers = consumers
    self.producer_nodes = [host for host in ndn.net.hosts if host.name in self.producers]
    self.consumer_nodes = [host for host in ndn.net.hosts if host.name in self.consumers]
    self.start()

  def start(self):
    self.ndn.start()
    time.sleep(2)
    nfds = AppManager(self.ndn, self.ndn.net.hosts, Nfd, logLevel='DEBUG')

    for host in self.ndn.net.hosts:
      host.cmd('tshark -o ip.defragment:TRUE -o ip.check_checksum:FALSE -ni any -f "udp port 6363" -w {}.pcap &> /dev/null &'
               .format(host.name))
      #host.cmd('ndndump -i any &> {}.ndndump &'.format(host.name))
      time.sleep(0.005)


    # time.sleep(6)
    # copy the test.info file to system first and from there copy it to node directory
    Popen(['cp', 'test.info', '/usr/local/etc/ndn/ndnsd_default.info'],
           stdout=PIPE, stderr=PIPE).communicate()

  def startProducer(self):
    print("Starting producers")
    hostInfo = dict([])
    for host in self.producer_nodes: # if host.name not in consumer:
      hostName = host.name
      hostInfoFile = '{}/{}/ndnsd_{}.info'.format(self.args.workDir, hostName, hostName)
      appPrefix = '/ndnsd/{}/service-info'.format(hostName)

      Popen(['cp', '/usr/local/etc/ndn/ndnsd_default.info', hostInfoFile],
             stdout=PIPE, stderr=PIPE).communicate()

      host.cmd('infoedit -f {} -s required.appPrefix -v {}'.format(hostInfoFile,
                                                                   appPrefix))
      
      # routes registration to udp multicast face/ip
      # cmd = "nfdc face | grep '224.0.23.170' | awk '{split ($1, a, \"=\"); print a[2]}'"
      # face_id = host.cmd(cmd)

      Nfdc.registerRoute(host, '/discovery', '224.0.23.170')
      Nfdc.registerRoute(host, '/ndnsd', '224.0.23.170')

      # set sync and info prefix to multi-cast strategy
      Nfdc.setStrategy(host, '/discovery', Nfdc.STRATEGY_MULTICAST)
      Nfdc.setStrategy(host, appPrefix, Nfdc.STRATEGY_MULTICAST)

      # uncomment to enable sync log
      cmd = 'export NDN_LOG=ndnsd.*=TRACE:psync.*=TRACE:sync.*=TRACE'
      host.cmd(cmd)

      cmd = 'ndnsd-producer {} 1 &> {}/{}/producer.log &'.format(hostInfoFile,
                                                                 self.args.workDir,
                                                                 hostName)
      host.cmd(cmd)

      time.sleep(5)

  def startConsumer(self):
    print("Staring consumers")
    for consumer in self.consumer_nodes:
      cName = consumer.name
      # uncomment to enable sync log
      cmd = 'export NDN_LOG=ndnsd.*=TRACE:psync.*=TRACE:sync.*=TRACE'
      consumer.cmd(cmd)

      # routes registration to udp multicast face/ip
      # cmd = "nfdc face | grep '224.0.23.170' | awk '{split ($1, a, \"=\"); print a[2]}'"
      # face_id = consumer.cmd(cmd)
      Nfdc.registerRoute(consumer, '/discovery', '224.0.23.170')
      Nfdc.registerRoute(consumer, '/ndnsd', '224.0.23.170')

      # set multi-cast strategy for sync prefix
      Nfdc.setStrategy(consumer, '/discovery', Nfdc.STRATEGY_MULTICAST)

      cmd = 'ndnsd-consumer -s {} &> {}/{}/consumer.log -c 1 -p 1 &'.format(self.consumers[cName],
                                                                            self.args.workDir, cName)
      consumer.cmd(cmd)

      # sleep for a while to let consumer boot up properly
      time.sleep(2)

if __name__ == '__main__':
    setLogLevel('info')

    subprocess.call(['rm','-r','/tmp/minindn/'])

    producers = dict()
    consumers = dict()
    producers['p1'] = ['printer', 100] #{"<sp-name>": ['service-name', 'lifetime in ms']}
    producers['p2'] = ['printer', 100]
    producers['p3'] = ['printer', 100]
    producers['p4'] = ['printer', 100]
    consumers = {'a':'printer', 'b':'printer', 'c':'printer'} #['<consumer-name>']
    # consumers = {'c1':'printer'} #['<consumer-name>']

    ndn = Minindn()
    exp = NDNSDExperiment(ndn.args, producers, consumers)

    # # For all host, pass ndn.net.hosts or a list, [ndn.net['a'], ..] or [ndn.net.hosts[0],.]
    # info('Adding static routes to NFD\n')
    # grh = NdnRoutingHelper(ndn.net)

    # for host in exp.producer_nodes:
    #   hostName = host.name
    #   appPrefix = '/ndnsd/'+hostName+'/service-info'
    #   discoveryPrefix = '/discovery/{}'.format(exp.producers[hostName][0])
    #   grh.addOrigin([host], [appPrefix, discoveryPrefix])

    # # grh.calculateNPossibleRoutes(1)

    exp.startProducer()
    exp.startConsumer()

    # # need to give some time for sync convergence
    # time.sleep(10)

    # need to run reload at producers node
    print("Staring experiment, i.e. reloading producers, \
          approximate time to complete: {} seconds".format(numberOfUpdates + jitter))
    for host in exp.producer_nodes:
      cmd = 'ndnsd-reload -c {} -i {} -r {} &> {}/{}/reload.log &'.format(numberOfUpdates,
                                                                   exp.producers[host.name][1]-10,
                                                                   200, ndn.args.workDir,
                                                                   host.name)
      host.cmd(cmd)

    # approximate time to complete the experiment
    print("Sleep approximately {} seconds to complete \
          the experiment".format(numberOfUpdates + jitter))
    time.sleep(numberOfUpdates + jitter)
    print("Experiment completed")

    ndn.stop()
    MiniNDNCLI(ndn.net)
