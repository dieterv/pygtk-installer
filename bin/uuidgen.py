#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2010 pygtk-installer Contributors
#
# This file is part of pygtk-installer.
#
# pygtk-installer is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pygtk-installer is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pygtk-installer. If not, see <http://www.gnu.org/licenses/>.


import uuid


if __name__ == '__main__':
    print '{%s}' % str(uuid.uuid4()).upper()
