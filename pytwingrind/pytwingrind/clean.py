#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import logging
from pytwingrind import common

def remove_guards(filepath: str, fb_name: str):
    """remove guards to fb and all methods for this file"""

    encoding = common.detect_encoding(filepath)
    with open(filepath, "rt", encoding=encoding) as f:
        src = f.read()
        src, i = re.subn(r'{tag}Twingrind\.Profiler\.Push.*?{tag}\r?\n'.format(tag=re.escape(common.profiler_tag)), '', src, 0, re.M | re.UNICODE)
        src, j = re.subn(r'{tag}Twingrind\.Profiler\.Pop.*?{tag}RETURN'.format(tag=re.escape(common.profiler_tag)), 'RETURN', src, 0, re.M | re.UNICODE)
        src, k = re.subn(r'\r?\n{tag}Twingrind\.Profiler\.Pop.*?{tag}'.format(tag=re.escape(common.profiler_tag)), '', src, 0, re.M | re.UNICODE)        
        logging.debug("{}: removed {} guards".format(fb_name, int(i))) # we should have 2 guards per method


    with open(filepath, "wt", encoding=encoding) as g:
        g.write(src)

def run(filepath: str):

    for f in common.find_sourcefiles(filepath):
        fb_name, _ = os.path.splitext(os.path.basename(f))
        remove_guards(f, fb_name)  
