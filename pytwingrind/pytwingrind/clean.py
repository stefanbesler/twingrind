#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import logging
from pytwingrind import common

def remove_guards(filepath: string, fb_name: string):
    """remove guards to fb and all methods for this file"""

    encoding = common.detect_encoding(filepath)
    with open(filepath, "rt", encoding=encoding) as f:
        src = f.read()
        src_new, i = re.subn(r'([\s\n]*){tag}.*?{tag}[\s\n]*'.format(tag=re.escape(common.profiler_tag)), '\1', src, 0, re.S | re.M | re.UNICODE)

        logging.debug("{}: guards removed in {} methods".format(fb_name, int(i/2))) # we should have 2 guards per method


    with open(filepath, "wt", encoding=encoding) as g:
        g.write(src_new)

def run(dest: str):

    for f in common.find_sourcefiles(filepath):
        fb_name, _ = os.path.splitext(os.path.basename(f))
        remove_guards(f, fb_name)  
