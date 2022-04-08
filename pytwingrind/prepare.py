#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import logging
import pickle
import copy
import datetime
from argparse import ArgumentParser

parser = ArgumentParser("""adds or removes guards to TwinCAT3 function blocks.
These guards are used for profiling your program""")
parser.add_argument("-d", "--directory", help="directory containing all function blocks that profiling guards should be modified", required=True)
parser.add_argument("-m", "--hashmap", help="hash map")
parser.add_argument("-a", "--action", help="whether guards should be added or removed", choices=["add", "remove"], required=True)
args = vars(parser.parse_args())

logging.basicConfig(level=logging.DEBUG)

filepath = args['directory']
action = args['action']
dest = args['hashmap']
tag = r"(* @@ PROFILER @@ *)"

def create_hash(fb, method, hashes):
    increment = 0
    while True:
        hstr = fb + "::" + method + str(increment)
        h = hash(hstr) & 4294967295
        if h not in hashes:
            hashes[h] = (fb, method)
            return h
        increment += 1

def find_files(filepath):
    """walk recursively through folders and look for TwinCat3 source files"""

    for subdir, _, files in os.walk(filepath):
        for f in files:
            re_source = re.match(".*.tcpou$", f, re.I) 
            if re_source:
                yield os.path.join(subdir, f)


def add_guards(filepath, fb_name, hashes):
    """add guards to fb and all methods for this file"""

    src = ""
    
    try:
        with open(filepath, "rt") as f:
            src = f.read()
            if tag in src:
                logging.warning("Profiler guards seem already present in {}, skipping".format(fb_name))
                return
    except UnicodeDecodeError as ex:
        print('File {} contains invalid characters, only ascii is supported'.format(filepath))
        raise ex

    # add guards to function blocks
    functionblocks = re.findall(r'<POU(.*?)Name="(.*?)"(.*?)FUNCTION_BLOCK(.*?)<ST><!\[CDATA\[(.*?)\]\]><\/ST>', src, re.S | re.M | re.UNICODE)
    nearly = 0
    ncallables = 0
    if functionblocks:
        for m in functionblocks:
            functionblock_name = m[1]
            body = m[4]
            old_body = copy.deepcopy(body)
            hash = create_hash(fb_name, functionblock_name, hashes)

            body = '''{tag}Twingrind.Profiler.Push({hash});{tag}\n'''.format(hash=hash, tag=tag) + body
            body, i = re.subn(r'RETURN([\s]*?);',
                              r'''\1{tag}Twingrind.Profiler.Pop({hash}); {tag}\1RETURN;'''.format(hash=hash, tag=tag),
                              body, 0, re.S | re.M | re.UNICODE)
            body = body + '''\n{tag}Twingrind.Profiler.Pop({hash});{tag}'''.format(hash=hash, tag=tag)

            nearly += i # two guards are always added
            ncallables += 1

            src = src.replace(r'<POU{spacer0}Name="{functionblock_name}"{spacer2}FUNCTION_BLOCK{spacer3}<ST><![CDATA[{body}]]></ST>'.format(spacer0=m[0],
                                                                                          functionblock_name=functionblock_name,
                                                                                          spacer2=m[2],
                                                                                          spacer3=m[3],
                                                                                          body=old_body,
                                                                                          fb=fb_name),
                              r'<POU{spacer0}Name="{functionblock_name}"{spacer2}FUNCTION_BLOCK{spacer3}<ST><![CDATA[{body}]]></ST>'.format(spacer0=m[0],
                                                                                          functionblock_name=functionblock_name,
                                                                                          spacer2=m[2],
                                                                                          spacer3=m[3],
                                                                                          body=body,
                                                                                          fb=fb_name))

    # add guards to all methods
    methods = re.findall(r'<Method(.*?)Name="(.*?)"(.*?)<ST><!\[CDATA\[(.*?)\]\]><\/ST>', src, re.S | re.M | re.UNICODE)
    if methods:
        for m in methods:
            if ' ABSTRACT ' in m[2]:
                continue
            
            method_name = m[1]
            body = m[3]
            old_body = copy.deepcopy(body)
            hash = create_hash(fb_name, method_name, hashes)

            body = '''{tag}Twingrind.Profiler.Push({hash});{tag}\n'''.format(hash=hash, tag=tag) + body
            body, i = re.subn(r'RETURN([\s]*?);',
                              r'''\1{tag}Twingrind.Profiler.Pop({hash}); {tag}\1RETURN;'''.format(hash=hash, tag=tag),
                              body, 0, re.S | re.M | re.UNICODE)
            body = body + '''\n{tag}Twingrind.Profiler.Pop({hash});{tag}'''.format(hash=hash, tag=tag)

            nearly += i # two guards are always added
            ncallables += 1

            src = src.replace(r'<Method{spacer0}Name="{method_name}"{spacer2}<ST><![CDATA[{body}]]></ST>'.format(spacer0=m[0],
                                                                                          method_name=method_name,
                                                                                          spacer2=m[2],
                                                                                          body=old_body,
                                                                                          fb=fb_name),
                              r'<Method{spacer0}Name="{method_name}"{spacer2}<ST><![CDATA[{body}]]></ST>'.format(spacer0=m[0],
                                                                                          method_name=method_name,
                                                                                          spacer2=m[2],
                                                                                          body=body,
                                                                                          fb=fb_name))



    logging.debug("{}: guards added in {} methods, contains ({} returns)".format(fb_name, ncallables, nearly+1))

    with open(filepath, "wt") as g:
        g.write(src)


def remove_guards(filepath, fb_name):
    """remove guards to fb and all methods for this file"""

    with open(filepath, "rt") as f:
        src = f.read()
        src_new, i = re.subn(r'([\s\n]*){tag}.*?{tag}[\s\n]*'.format(tag=re.escape(tag)), '\1', src, 0, re.S | re.M | re.UNICODE)

        logging.debug("{}: guards removed in {} methods".format(fb_name, int(i/2))) # we should have 2 guards per method


    with open(filepath, "wt") as g:
        g.write(src_new)

def main():
    hashes = {}
    hash_path = dest

    try:
        hashes = pickle.load(open(hash_path, 'rb'))
        logging.info('Updating an existing hashfile')
    except:
        logging.info('Creating a new hashfile')

    main_hash = 0 # hash for main.prg is fixed
    if action == "add":
        hashes[main_hash] = ('MAIN', 'MAIN')

    for f in find_files(filepath):
        fb_name, _ = os.path.splitext(os.path.basename(f))

        if action == "add":
            add_guards(f, fb_name, hashes)
        elif action == "remove":
            remove_guards(f, fb_name)
        else:
            raise Exception('Invalid action {} use [add, remove]'.format(action))

    if action == "add":
        pickle.dump(hashes, open(hash_path, "wb"))
        print('Hashmap location={}'.format(hash_path))
        print('Containing {} hashes'.format(len(hashes)))
        print('Do not forget to add the boilerplate code with hash=0 in your MAIN.PRG'.format(main_hash))    

# main
if __name__ == '__main__':
    main()
