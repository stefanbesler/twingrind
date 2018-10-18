#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import logging
from argparse import ArgumentParser

parser = ArgumentParser("""adds or removes guards to TwinCAT3 function blocks.
These guards are used for profiling your program""")
parser.add_argument("-d", "--directory", help="directory containing all function blocks that profiling guards should be modified", required=True)
parser.add_argument("-a", "--action", help="whether guards should be added or removed", choices=["add", "remove"], required=True)
args = vars(parser.parse_args())

logging.basicConfig(level=logging.DEBUG)

filepath = args['directory']
action = args['action']
tag = r"(* @@ PROFILER @@ *)"

def find_files(filepath):
    """walk recursively through folders and look for TwinCat3 source files"""

    for subdir, _, files in os.walk(filepath):
        for f in files:
            re_source = re.match(".*.tcpou$", f, re.I) 
            if re_source:
                yield os.path.join(subdir, f)


def add_guards(filepath):
    """add guards to fb and all methods for this file"""
    global tag

    filename, _ = os.path.splitext(os.path.basename(filepath))

    with open(filepath, "rt") as f:
        src = f.read()
        if tag in src:
            logging.warning("profiler guards seem already present in {}, skipping".format(os.path.basename(f)))
            return

        src_new,i = re.subn(r'<Method(.*?)Name="(.*?)"(.*?)<ST><!\[CDATA\[(.*?)\]\]><\/ST>',
                            r'<Method\1Name="\2"\3<ST><![CDATA[{tag}Profiler.pushMethod("{fb}", "\2"); {tag}\n\4\n{tag}Profiler.popMethod("{fb}", "\2"); {tag}]]></ST>'.format(fb=filename, tag=tag), src, 0, re.S | re.M | re.UNICODE)

        if i == 0:
            logging.information("no profile guards added!")
        else:
            logging.debug("{}: guards added in {} methods".format(filename, i))



    with open(filepath, "wt") as g:
        g.write(src_new)


def remove_guards(filepath):
    """remove guards to fb and all methods for this file"""
    global tag

    filename, _ = os.path.splitext(os.path.basename(filepath))

    with open(filepath, "rt") as f:
        src = f.read()
        src_new,i = re.subn(r'[\s\n]*{tag}.*?{tag}[\s\n]*'.format(tag=re.escape(tag)), '', src, 0, re.S | re.M | re.UNICODE)

        if i == 0:
            logging.information("no profile guards removed!")
        else:
            logging.debug("{}: guards removed in {} methods".format(filename, int(i/2))) # we should have 2 guards per method



    with open(filepath, "wt") as g:
        g.write(src_new)


for f in find_files(filepath):
    if action == "add": 
        add_guards(f)
    elif action == "remove":
        remove_guards(f)
    else:
        raise Exception('invalid action {}'.format(action))
