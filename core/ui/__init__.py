"""
This file is part of Giswater 3
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
__author__ = 'David Erill'
__date__ = 'January 2016'
__copyright__ = '(C) 2016, David Erill'

# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

import os
import sys

curpath = os.path.dirname(os.path.realpath(__file__))

# Adding so that our UI files can find resources_rc.py which is up one level.
sys.path.append(os.path.join(curpath, '..'))
