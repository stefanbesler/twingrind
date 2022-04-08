import os
import sys
import re
import logging
import time
import datetime
from argparse import ArgumentParser
import pyads
import ctypes
import glob
import pandas
import pickle
import networkx
import pandas as pd
from plcstack import Call

class Stack(ctypes.Structure):
    _fields_ = [("calls", Call * (320000))]

def extract_stack(stack, hashmap):
    nmainhash = 0
    lst = []
    
    dt = 0
    for call in stack.calls:
        fb, method = hashmap.get(call.hash, (str(call.hash), str(call.hash)))
        if fb == 'MAIN':
            nmainhash += 1
                        
        lst.append([fb, method, call.depth, call.starthi, call.startlo, call.endhi, call.endlo, call.hash])

        if nmainhash >= 2:
            return lst

    return lst


def build_graph(network, node_start, data, sid, eid, depth=0):
    global log,d
    if eid <= sid:
        return;

    lastid = -1
    for startid,dstart in data.loc[sid:, :].iterrows():
        if startid >= lastid:
            for endid,dend in data.loc[startid+1:eid,:].iterrows():
                if dstart.hash == dend.hash and dstart.depth == dend.depth:
                    # insert fb node
                    dt_us = 0.1 * (((dend.endhi << 32) + (dend.endlo)) - ((dstart.starthi << 32) + (dstart.startlo)))

                    if network.has_edge(node_start, startid):
                        network[node_start][startid]['attr_dict']['calls'] += 1
                        network[node_start][startid]['attr_dict']['dt_us'] += [dt_us,]
                    else:
                        network.add_edge(node_start, startid, attr_dict={'dt_us': [dt_us,], 'calls': 1, 'name': '{}::{}'.format(dstart.fb, dstart.method)})

                    logging.info((' '*depth) + '{}::{} ({} ns) [{}, {}]'.format(dstart.fb, dstart.method, int(dt_us * 1000), startid, endid))
                    build_graph(network, startid, data, startid+1, endid-1, depth+1)

                    lastid = endid+1
                    break
                


def write_callgrind(network, f, selfcost, node_start=0, node_name='MAIN::MAIN', depth=0):

    ch = lambda x, y: x + '::' + y if len(y) > 0 else x

    # defaulting to cycle time 1 ms if nothing else is specified
    if selfcost < 0 and depth == 0:
        selfcost = 1000000000;
    elif selfcost < 0:
        raise Expection('selfcost < 0')

    # write header information
    if depth == 0:
        main_dt = network.get_edge_data('root', 0)['attr_dict']['dt_us'][0] * 1000
        f.write('events: dt')
        f.write('\nfl={}\n'.format(ch('CYCLE', '')))
        f.write('fn={}\n'.format(ch('CYCLE', 'CYCLE')))
        f.write('{} {}\n'.format(1, int(selfcost - main_dt))) # self cost
        f.write('cfl={}\n'.format(ch('MAIN', '')))
        f.write('cfn={}\n'.format(ch('MAIN', 'MAIN')))        
        f.write('calls={} {}\n'.format(1, 1))
        f.write('{} {}\n'.format(0, int(main_dt))) # cost of main prg
        selfcost = main_dt
        
    # calculate self costs by substracting the costs of all calls
    for _, n in enumerate(network.neighbors(node_start)):
        for dt_us in network.get_edge_data(node_start, n)['attr_dict']['dt_us']:
            selfcost -= int(dt_us*1000)
        
    for _, n in enumerate(network.neighbors(node_start)):
        print("depth" + str(depth) + "node: " + node_name  +" n: " + network.get_edge_data(node_start, n)['attr_dict']['name'])        
            
    if(depth > 12):            
        import sys
        sys.exit(-1)        
        
    node_fb, node_method = node_name.split('::')
    f.write('\nfl={}\n'.format(ch(node_fb, '')))
    f.write('fn={}\n'.format(ch(node_fb, node_method)))
    f.write('{} {}\n'.format(1, selfcost))
    for i,n in enumerate(network.neighbors(node_start)):
        fb, method = network.get_edge_data(node_start, n)['attr_dict']['name'].split('::')

        calls = network.get_edge_data(node_start, n)['attr_dict']['calls']
        dts = network.get_edge_data(node_start, n)['attr_dict']['dt_us']

        for c in range(calls):
            f.write('cfl={}\n'.format(ch(fb, '')))
            f.write('cfn={}\n'.format(ch(fb, method)))
            f.write('calls={} {}\n'.format(1, 1))
            f.write('{} {}\n'.format(i, int(dts[c]*1000)))

    for i,n in enumerate(network.neighbors(node_start)):
        dt_us = network.get_edge_data(node_start, n)['attr_dict']['dt_us']
        n_name = network.get_edge_data(node_start, n)['attr_dict']['name']
        write_callgrind(network, f, selfcost=int(max(dt_us)*1000), node_start=n, node_name=n_name, depth=depth+1)



def reconstruct(hashmap_filepath, callstack_filepath, dest, args):

    stack = pickle.load(open(callstack_filepath, 'rb'))
    hm = pickle.load(open(hashmap_filepath, 'rb'))

    lst = extract_stack(stack, hm)
    print(lst[0])
    data = pd.DataFrame(lst, columns=['fb', 'method', 'depth', 'starthi', 'startlo', 'endhi', 'endlo', 'hash'])

    n = networkx.DiGraph()
    build_graph(n, 'root', data, 0, len(lst) - 1)
    
    if args and args['graph']:
        import matplotlib.pyplot as plt
        networkx.draw(n, with_labels=True)
        plt.show()    
    
    logging.info('{} entries in callstack'.format(int(len(lst) / 2)))

    with open(os.path.join(dest, 'callgrind.{}'.format(os.path.basename(callstack_filepath))), 'wt') as f:
        write_callgrind(n, f, int(args['cycletime_ms'] * 1000000))


if __name__ == '__main__':
    parser = ArgumentParser("""triggers the measurement of a single profile and
    stores the corresponding callstack on disk""")

    parser.add_argument("-m", "--hashmap", help="hash map")
    parser.add_argument("-c", "--callstack", help="callstack")
    parser.add_argument("-s", "--source", help="folder containing several callstacks and 1 hashmap")
    parser.add_argument("-d", "--dest", help="output directory ", default="./")
    parser.add_argument("-g", "--graph", help="output directory ", action="store_true")
    parser.add_argument("-t", "--cycletime_ms", help="plc cycletime in milliseconds", default=1)
    parser.add_argument("-q", "--masquarade", help="hash fb and methodnames", action="store_true")
    args = vars(parser.parse_args())

    logging.basicConfig(level=logging.INFO)

    if args['source']:
        hashmap_filepath = glob.glob(os.path.join(args['source'], 'hashmap*'))[0]
        callstacks = glob.glob(os.path.join(args['source'], 'callstack*'))
        dest = args['source']
    else:
        hashmap_filepath = args['hashmap']
        callstacks = [ args['callstack'], ]
        dest = args['dest']

    for c in callstacks:
        reconstruct(hashmap_filepath, c, dest, args)
