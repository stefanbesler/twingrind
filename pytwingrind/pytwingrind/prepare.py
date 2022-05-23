#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import logging
import pickle
from pytwingrind import common

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
        with open(filepath, "rt", encoding=common.detect_encoding(filepath)) as f:
            src = f.read()
            if common.profiler_tag in src:
                logging.warning("Profiler guards seem already present in {}, skipping".format(fb_name))
                return
    except UnicodeDecodeError as ex:
        print('File {} contains invalid characters, only ascii is supported'.format(filepath))
        raise ex

    nearly = 0
    ncallables = 0
    
    # add guards to functions
    functions = re.findall(r'<POU(.*?)Name="(.*?)"(.*?)FUNCTION (.*?)<ST><!\[CDATA\[(.*?)\]\]><\/ST>', src, re.S | re.M | re.UNICODE)
    if functions:
        for m in functions:
            function_name = m[1]
            body = m[4]
            old_body = body
            hash = create_hash(fb_name, function_name, hashes)

            body = '''{tag}Twingrind.Profiler.Push({hash});{tag}\n'''.format(hash=hash, tag=common.profiler_tag) + body
            body, i = re.subn(r'RETURN([\s]*?);',
                              r'''\1{tag}Twingrind.Profiler.Pop({hash}); {tag}\1RETURN;'''.format(hash=hash, tag=common.profiler_tag),
                              body, 0, re.S | re.M | re.UNICODE)
            body = body + '''\n{tag}Twingrind.Profiler.Pop({hash});{tag}'''.format(hash=hash, tag=common.profiler_tag)

            nearly += i # two guards are always added
            ncallables += 1

            src = src.replace(r'<POU{spacer0}Name="{function_name}"{spacer2}FUNCTION {spacer3}<ST><![CDATA[{body}]]></ST>'.format(spacer0=m[0],
                                                                                          function_name=function_name,
                                                                                          spacer2=m[2],
                                                                                          spacer3=m[3],
                                                                                          body=old_body),
                              r'<POU{spacer0}Name="{function_name}"{spacer2}FUNCTION {spacer3}<ST><![CDATA[{body}]]></ST>'.format(spacer0=m[0],
                                                                                          function_name=function_name,
                                                                                          spacer2=m[2],
                                                                                          spacer3=m[3],
                                                                                          body=body))

    # add guards to programs
    programs = re.findall(r'<POU(.*?)Name="(.*?)"(.*?)PROGRAM(.*?)<ST><!\[CDATA\[(.*?)\]\]><\/ST>', src, re.S | re.M | re.UNICODE)
    if programs:
        for m in programs:
            prg_name = m[1]
            body = m[4]
            old_body = body
            hash = create_hash(fb_name, prg_name, hashes)

            body = '''{tag}Twingrind.Profiler.Push({hash});{tag}\n'''.format(hash=hash, tag=common.profiler_tag) + body
            body, i = re.subn(r'RETURN([\s]*?);',
                              r'''\1{tag}Twingrind.Profiler.Pop({hash}); {tag}\1RETURN;'''.format(hash=hash, tag=common.profiler_tag),
                              body, 0, re.S | re.M | re.UNICODE)
            body = body + '''\n{tag}Twingrind.Profiler.Pop({hash});{tag}'''.format(hash=hash, tag=common.profiler_tag)

            nearly += i # two guards are always added
            ncallables += 1

            src = src.replace(r'<POU{spacer0}Name="{prg_name}"{spacer2}PROGRAM{spacer3}<ST><![CDATA[{body}]]></ST>'.format(spacer0=m[0],
                                                                                          prg_name=prg_name,
                                                                                          spacer2=m[2],
                                                                                          spacer3=m[3],
                                                                                          body=old_body),
                              r'<POU{spacer0}Name="{prg_name}"{spacer2}PROGRAM{spacer3}<ST><![CDATA[{body}]]></ST>'.format(spacer0=m[0],
                                                                                          prg_name=prg_name,
                                                                                          spacer2=m[2],
                                                                                          spacer3=m[3],
                                                                                          body=body))

    # add guards to function blocks
    functionblocks = re.findall(r'<POU(.*?)Name="(.*?)"(.*?)FUNCTION_BLOCK(.*?)<ST><!\[CDATA\[(.*?)\]\]><\/ST>', src, re.S | re.M | re.UNICODE)
    if functionblocks:
        for m in functionblocks:
            functionblock_name = m[1]
            body = m[4]
            old_body = body
            hash = create_hash(fb_name, functionblock_name, hashes)

            body = '''{tag}Twingrind.Profiler.Push({hash});{tag}\n'''.format(hash=hash, tag=common.profiler_tag) + body
            body, i = re.subn(r'RETURN([\s]*?);',
                              r'''\1{tag}Twingrind.Profiler.Pop({hash}); {tag}\1RETURN;'''.format(hash=hash, tag=common.profiler_tag),
                              body, 0, re.S | re.M | re.UNICODE)
            body = body + '''\n{tag}Twingrind.Profiler.Pop({hash});{tag}'''.format(hash=hash, tag=common.profiler_tag)

            nearly += i # two guards are always added
            ncallables += 1

            src = src.replace(r'<POU{spacer0}Name="{functionblock_name}"{spacer2}FUNCTION_BLOCK{spacer3}<ST><![CDATA[{body}]]></ST>'.format(spacer0=m[0],
                                                                                          functionblock_name=functionblock_name,
                                                                                          spacer2=m[2],
                                                                                          spacer3=m[3],
                                                                                          body=old_body),
                              r'<POU{spacer0}Name="{functionblock_name}"{spacer2}FUNCTION_BLOCK{spacer3}<ST><![CDATA[{body}]]></ST>'.format(spacer0=m[0],
                                                                                          functionblock_name=functionblock_name,
                                                                                          spacer2=m[2],
                                                                                          spacer3=m[3],
                                                                                          body=body))

    # add guards to all methods
    methods = re.findall(r'<Method(.*?)Name="(.*?)"(.*?)<ST><!\[CDATA\[(.*?)\]\]><\/ST>', src, re.S | re.M | re.UNICODE)
    if methods:
        for m in methods:
            if ' ABSTRACT ' in m[2]:
                continue
            
            method_name = m[1]
            body = m[3]
            old_body = body
            hash = create_hash(fb_name, method_name, hashes)

            body = '''{tag}Twingrind.Profiler.Push({hash});{tag}\n'''.format(hash=hash, tag=common.profiler_tag) + body
            body, i = re.subn(r'RETURN([\s]*?);',
                              r'''\1{tag}Twingrind.Profiler.Pop({hash}); {tag}\1RETURN;'''.format(hash=hash, tag=common.profiler_tag),
                              body, 0, re.S | re.M | re.UNICODE)
            body = body + '''\n{tag}Twingrind.Profiler.Pop({hash});{tag}'''.format(hash=hash, tag=common.profiler_tag)

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

    with open(filepath, "wt", encoding=common.detect_encoding(filepath)) as g:
        g.write(src)



def run(filepath : str, hashmap : str):
    hashes = {}

    try:
        hashes = pickle.load(open(hashmap, 'rb'))
        logging.info('Updating an existing hashfile')
    except:
        logging.info('Creating a new hashfile')

    for f in find_files(filepath):
        fb_name, _ = os.path.splitext(os.path.basename(f))
        add_guards(f, fb_name, hashes)

    pickle.dump(hashes, open(hashmap, "wb"))
    print('Hashmap location={}'.format(hashmap))
    print('Containing {} hashes'.format(len(hashes)))
    print('Do not forget to call Twingrind.Profiler() in the  *first line* of the *first PRG* in the PLC task!')
    print('''
MAIN.PRG
-------------------------------
1 Twingrind.Profiler();
2
3 // <Already existing source code here>
4 // <Already existing source code here>
5 // <Already existing source code here>
.
.
''')
