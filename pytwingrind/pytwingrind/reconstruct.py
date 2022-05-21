import os
import logging
import pickle
import inspect
import networkx
import numpy as np
import ctypes
from pytwingrind import common
from enum import IntEnum
from pytwingrind.common import Call


class StackRow(IntEnum):
    DEPTH = 0
    START_US = 1
    END_US = 2
    HASH = 3


def extract_stack(stack, hashmap):
    data = np.zeros((len(stack.calls), 4), dtype=np.uint64)
    size = 0
    def hilo_to_lword(hi, lo): return ((hi << 32) + lo)
    
    for call in stack.calls:
        data[size] = [call.depth, 0.1 * hilo_to_lword(
            call.starthi, call.startlo), 0.1 * hilo_to_lword(call.endhi, call.endlo), call.hash]

        # no more valid timestamps
        if np.all(data[size] == 0):
            break;
        size = size + 1

    logging.info(f"Extracted {int(size/2)} calls")
    return data[0:size]


def build_graph(network, hashmap, roots, data, sid=-1, eid=-1):

    if sid < 0 and eid < 0:
        sid = 0
        eid = len(data)

    endid = np.where(np.logical_and(data[sid+1:eid, StackRow.HASH] == data[sid, StackRow.HASH],
                     data[sid+1:eid, StackRow.DEPTH] == data[sid, StackRow.DEPTH]))[0][0] + sid + 1
    dt_us = data[endid, StackRow.END_US] - data[sid, StackRow.START_US]
    fb, method = hashmap[data[endid, StackRow.HASH]]
    depth = int(data[endid, StackRow.DEPTH])+1

    roots = roots[0:depth]
    parent = roots[-1]

    if network.has_edge(parent, sid):
        network[parent][sid]['attr_dict']['calls'] += 1
        network[parent][sid]['attr_dict']['dt_us'] += [dt_us, ]
    else:
        network.add_edge(parent, sid, attr_dict={
                         'dt_us': [dt_us, ], 'calls': 1, 'name': '{}::{}'.format(fb, method)})

    if sid+1 != endid:
        build_graph(network, hashmap, roots + [sid], data, sid+1, endid)

    if(endid+1 < len(data)) and endid+1 != eid:
        build_graph(network, hashmap, roots, data, endid+1, eid)


def write_callgrind(network, f, selfcost, node_start="root", node_name=None, depth=0):

    def ch(x, y): return x + '::' + y if len(y) > 0 else x

    # defaulting to cycle time 1 ms if nothing else is specified
    if selfcost < 0 and depth == 0:
        selfcost = 1000000000
    elif selfcost < 0:
        raise Exception('selfcost < 0')

    # write header information
    if depth == 0:
        f.write('events: dt')
        f.write('\nfl={}\n'.format(ch('Task', '')))
        f.write('fn={}\n'.format(ch('Task', 'Task')))
        f.write('{} {}\n'.format(1, int(selfcost)))  # self cost

    # calculate self costs by substracting the costs of all calls
    for _, n in enumerate(network.neighbors(node_start)):
        for dt_us in network.get_edge_data(node_start, n)['attr_dict']['dt_us']:
            selfcost -= int(dt_us*1000)

    if node_name is not None:
        node_fb, node_method = node_name.split('::')
        f.write('\nfl={}\n'.format(ch(node_fb, '')))
        f.write('fn={}\n'.format(ch(node_fb, node_method)))
        f.write('{} {}\n'.format(1, selfcost))
    for i, n in enumerate(network.neighbors(node_start)):
        fb, method = network.get_edge_data(
            node_start, n)['attr_dict']['name'].split('::')

        calls = network.get_edge_data(node_start, n)['attr_dict']['calls']
        dts = network.get_edge_data(node_start, n)['attr_dict']['dt_us']

        for c in range(calls):
            f.write('cfl={}\n'.format(ch(fb, '')))
            f.write('cfn={}\n'.format(ch(fb, method)))
            f.write('calls={} {}\n'.format(1, 1))
            f.write('{} {}\n'.format(i, int(dts[c]*1000)))

    for i, n in enumerate(network.neighbors(node_start)):
        dt_us = network.get_edge_data(node_start, n)['attr_dict']['dt_us']
        n_name = network.get_edge_data(node_start, n)['attr_dict']['name']
        write_callgrind(network, f, selfcost=int(max(dt_us)*1000),
                        node_start=n, node_name=n_name, depth=depth+1)


def run(hashmap: str, file: str, dest: str):

    logging.info(f"Reconstructing callstack {file}")
    
    # unpickling is tricky if the Stack class does not exist yet. The latter
    # occurs if we use 'twingrind reconstruct' instead of 'twingrind process'.
    # Lets create a "wrong" Stack class that can only hold 1 call, then use
    # load the file and use the max_stacksize, which is stored there, to create
    # the correct Stack class
    common.create_stack_class(1)
    callstack = pickle.load(open(file, 'rb'))
    common.create_stack_class(callstack.max_stacksize)
    callstack = pickle.load(open(file, 'rb'))
    
    logging.debug(f"Callstack max_stack={callstack.max_stacksize}")
    
    hm = pickle.load(open(hashmap, 'rb'))

    data = extract_stack(callstack.stack, hm)
    n = networkx.DiGraph()
    build_graph(n, hm, ['root'], data)

    logging.info(f'Reconstructed {int(len(data) / 2)} calls')
    filename = os.path.join(
        dest, 'callgrind.{}'.format(os.path.basename(file)))
    with open(filename, 'wt') as f:
        write_callgrind(n, f, int(callstack.cycletime * 100))
        logging.info(f'Reconstructed callgrind file to {filename}')
