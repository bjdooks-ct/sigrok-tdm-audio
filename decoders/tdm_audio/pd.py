##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2019 Ben Dooks <ben.dooks@codethink.co.uk>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

import sigrokdecode as srd

_max_channels = 8

class Decoder(srd.Decoder):
    api_version = 3
    id = 'tdm'
    name = 'TDM'
    longname = 'TDM Audio'
    desc = 'TDM multi-channel audio'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = []
    tags = ['Audio']
    channels = (
        { 'id': 'clock', 'name': 'bitclk', 'desc': 'Data bit clock' },
        { 'id': 'frame', 'name': 'framesync', 'desc': 'Frame sync' },
        { 'id': 'data', 'name': 'data', 'desc': 'Serial data' },
    )
    optional_channels = ()
    options = (
        {'id': 'bps', 'desc': 'Bits per sample', 'default':16 },
        {'id': 'channels', 'desc': 'Channels per frame', 'default':8 },
        {'id': 'edge', 'desc': 'Clock edge to sample on', 'default':'r', 'values': ('r', 'f') }
    )
    annotations = tuple(
        ('ch{}'.format(i), 'Channel {}'.format(i)) for i in range(_max_channels)
    ) + (
        ('warning', 'Warning'),
    )
    annotation_rows = (
        ('data', 'Data', tuple(range(_max_channels))),
        ('warnings', 'Warnings', (_max_channels,)),
    )

    def __init__(self, **kwargs):
        self.reset()

    def reset(self):
        # initialsation here
        self.samplerate = None
        self.channels = 8
        self.channel = 0
        self.bitdepth = 16
        self.bitcount = 0
        self.samplecount = 0
        self.lastsync = 0
        self.lastframe = 0
        self.data = 0
        self.ss_block = None

    def metdatadata(self, key, value):
        if key == srd.SRC_CONF_SAMPLERATE:
            self.samplerate = value

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.bitdepth = self.options['bps']
        self.edge = self.options['edge']

    def decode(self):
       while True:
           # wait for edge of clock (sample on rising/falling edge)
           clock, frame, data =  self.wait({0: self.edge})

           self.data = (self.data << 1) | data
           self.bitcount += 1

           if self.ss_block is not None:
               if self.bitcount >= self.bitdepth:
                   self.bitcount = 0
                   self.channel += 1

                   c1 = 'Channel %d' % self.channel
                   c2 = 'C%d' % self.channel
                   c3 = '%d' % self.channel
                   if self.bitdepth <= 8:
                       v = '%02x' % self.data
                   elif self.bitdepth <= 16:
                       v = '%04x' % self.data
                   else:
                       v = '%08x' % self.data

                   if self.channel < self.channels:
                       ch = self.channel
                   else:
                       ch = 0

                   self.put(self.ss_block, self.samplenum, self.out_ann,
                            [ch, ['%s: %s' % (c1, v),
                                 '%s: %s' % (c2, v),
                                 '%s: %s' % (c3, v) ]])
                   self.data = 0
                   self.ss_block = self.samplenum
                   self.samplecount += 1

           # check for new frame
           # note, frame may be a single clock, or active for the first
           # sample in the frame
           if frame != self.lastframe and frame == 1:
               self.channel = 0
               self.bitcount = 0
               self.data = 0
               if self.ss_block is None:
                   self.ss_block = 0

           self.lastframe = frame
