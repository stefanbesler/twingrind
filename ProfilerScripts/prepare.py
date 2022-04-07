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
parser.add_argument("-o", "--hash_directory", help="directory or file where the generated hashmap is stored (if action=add). If parameter is a file the hash gets updated.", required=True)
parser.add_argument("-a", "--action", help="whether guards should be added or removed", choices=["add", "remove"], required=True)
args = vars(parser.parse_args())

logging.basicConfig(level=logging.DEBUG)

filepath = args['directory']
action = args['action']
dest = args['hash_directory']
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

    with open(filepath, "rt") as f:
        src = f.read()
        if tag in src:
            logging.warning("profiler guards seem already present in {}, skipping".format(fb_name))
            return

    methods = re.findall(r'<Method(.*?)Name="(.*?)"(.*?)<ST><!\[CDATA\[(.*?)\]\]><\/ST>', src, re.S | re.M | re.UNICODE)
    nearly = 0
    nmethods = 0
    if methods:
        for m in methods:
            method_name = m[1]
            body = m[3]
            old_body = copy.deepcopy(body)
            hash = create_hash(fb_name, method_name, hashes)

            body = '''{tag}ProfilerLib.Profiler.Push({hash});{tag}\n'''.format(hash=hash, tag=tag) + body
            body, i = re.subn(r'RETURN([\s]*?);',
                                r'''\1{tag}ProfilerLib.Profiler.Pop({hash}); {tag}\1RETURN;'''.format(hash=hash, tag=tag),
                                body, 0, re.S | re.M | re.UNICODE)
            body = body + '''\n{tag}ProfilerLib.Profiler.Pop({hash});{tag}'''.format(hash=hash, tag=tag)

            nearly += i # two guards are always added
            nmethods += 1

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



    logging.debug("{}: guards added in {} methods, contains ({} returns)".format(fb_name, nmethods, nearly+1))

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


# main
if __name__ == '__main__':
    hashes = {}
    hash_path = os.path.join(dest, "hashmap_{}".format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))

    try:
        hashes = pickle.load(open(dest, 'rb'))
        logging.info('updating hashfile')
        hash_path = dest
    except:
        logging.info('generating new hashfile')

    main_hash = 0
    if action == "add":
        hashes[main_hash] = ('MAIN', 'MAIN')

    for f in find_files(filepath):
        fb_name, _ = os.path.splitext(os.path.basename(f))

        if action == "add":
            add_guards(f, fb_name, hashes)
        elif action == "remove":
            remove_guards(f, fb_name)
        else:
            raise Exception('invalid action {}'.format(action))

    if action == "add":
        pickle.dump(hashes, open(hash_path, "wb"))
        print('hashmap location={}'.format(hash_path))
        print('containing {} hashes'.format(len(hashes)))
        print('use {} as hash in your MAIN'.format(main_hash))