import os
import logging
import glob
import pickle
import networkx
import pandas as pd
from pytwingrind.common import Call

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

                    #logging.info((' '*depth) + '{}::{} ({} ns) [{}, {}]'.format(dstart.fb, dstart.method, int(dt_us * 1000), startid, endid))
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



def run(hashmap: str, callstack: str, dest: str, cycletime: float):
    logging.info(f"Reconstructing callstack {callstack}")
    stack = pickle.load(open(callstack, 'rb'))
    hm = pickle.load(open(hashmap, 'rb'))

    lst = extract_stack(stack, hm)
    data = pd.DataFrame(lst, columns=['fb', 'method', 'depth', 'starthi', 'startlo', 'endhi', 'endlo', 'hash'])

    n = networkx.DiGraph()
    build_graph(n, 'root', data, 0, len(lst) - 1)
 
    logging.info(f'Reconstructed {int(len(lst) / 2)} calls')
    filename = os.path.join(dest, 'callgrind.{}'.format(os.path.basename(callstack)))
    with open(filename, 'wt') as f:
        write_callgrind(n, f, int(cycletime * 1000000))
        logging.info(f'Reconstructed callgrind file to {filename}')

