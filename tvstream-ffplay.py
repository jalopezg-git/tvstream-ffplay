#!/usr/bin/env python
"""
   tvstream-ffplay.py - Play streamed content from the console via `ffmpeg` 

   Copyright (C) 2021 Javier L. Gomez

   tvstream-ffplay.py is free software; you can redistribute it and/or
   modify it under the terms of the GNU General Public
   License as published by the Free Software Foundation; either
   version 2.1 of the License, or (at your option) any later version.

   This software is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public
   License along with this program; if not, see <https://www.gnu.org/licenses/>.
"""

from common.provider import ContentProvider
from provider import *
import logging
import subprocess, shlex, sys, getopt, time
from enum import Enum

_PROVIDERS = {c.__name__: c for c in ContentProvider.__subclasses__()}

_DEFAULT_PROVIDER = 'AtresplayerProvider'
_DEFAULT_SINK = 'ffplay'
_DEFAULT_USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0'
_AVSOURCE_RETRY_THRESHOLD = 10

def usage():
    print("Usage: %s [OPTION]... RESOURCE\n" % sys.argv[0])
    print("RESOURCE is either a channel name from the channel list or an URL.\n")
    print("OPTION can be one of:")
    print("  -h, --help              Show this usage message")
    print("  --log-level=N           Change the log level to N (10=debug 20=info 30=warning 40=error 50=critical)\n")

    print("  --param='KEY=VALUE'     Pass an additional parameter to a provider")
    print("  --list-providers        List the available providers")
    print("  -p, --provider=PRV      Use PRV as provider; default is `%s'" % _DEFAULT_PROVIDER)
    print("  -l, --list-channels     List available live channels\n")

    print("  -s, --sink=SINKCMD      Set SINKCMD as the sink; default is `%s'" % _DEFAULT_SINK)
    print("  --sink-args=ARGS        Additional arguments for the sink command\n")

    print("  --authenticate-as=USER  Authenticate as USER and save the authentication cookie")
    print("  --password=PASSWD       Use PASSWD for authentication (used with --authenticate-as=)")
    print("  --use-auth-cookie       Use saved authentication cookie for this request (see also --authenticate-as=)\n")

    print("  --list-alternatives     List available alternatives for the requested resource")
    print("  --alternative=N         Request alternative N\n\n")

    print("Examples:")
    print("  $ %s --list-channels" % sys.argv[0])
    print("  $ %s --list-alternatives 'Antena 3'" % sys.argv[0])
    print("  $ %s --sink-args='-vcodec h264_mmal -fs' --alternative=2 'laSexta'" % sys.argv[0])
    print("  $ %s --param='urls-per-proc=30' 'Antena 3'" % sys.argv[0])
    sys.exit(1)

class Operation(Enum):
    PLAY_RESOURCE = 0
    LIST_CHANNELS = 1
    AUTHENTICATE = 2
    LIST_ALTERNATIVES = 3

def main():
    logLevel = logging.INFO
    providerName = _DEFAULT_PROVIDER
    params = {'user-agent': _DEFAULT_USER_AGENT}
    useAuthCookie = False
    username, password = '', ''
    alternative = -1
    sinkCmdline = [_DEFAULT_SINK]
    op = Operation.PLAY_RESOURCE

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hp:s:la:',
                                   ['help', 'log-level=', 'param=',
                                    'list-providers', 'provider=',
                                    'sink=', 'sink-args=',
                                    'list-channels',
                                    'authenticate-as=', 'password=', 'use-auth-cookie',
                                    'list-alternatives', 'alternative='])
    except getopt.GetoptError as err:
        print(err)
        usage()

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        elif o == '--log-level':
            logLevel = int(a)
        elif o == '--param':
            k, v = a.split('=', 1)
            params[k] = v
        elif o == '--list-providers':
            for k in _PROVIDERS:
                print(k)
            sys.exit(0)
        elif o in ('-p', '--provider'):
            providerName = a
        elif o in ('-s', '--sink'):
            sinkCmdline[0] = a
        elif o == '--sink-args':
            sinkCmdline += shlex.split(a)
        elif o in ('-l', '--list-channels'):
            op = Operation.LIST_CHANNELS
        elif o == '--authenticate-as':
            op = Operation.AUTHENTICATE
            username = a
        elif o == '--password':
            password = a
        elif o == '--use-auth-cookie':
            useAuthCookie = True
        elif o == '--list-alternatives':
            op = Operation.LIST_ALTERNATIVES
        elif o in ('-a', '--alternative'):
            alternative = int(a)

    logging.basicConfig(format='[%(levelname)s] %(message)s', level=logLevel)
    if not username and password:
        logging.warning('No username specified via --authenticate-as=; ignoring password.')

    p = _PROVIDERS[providerName](params)
    try:
        if op != Operation.AUTHENTICATE and useAuthCookie:
            logging.info('Using previous authentication cookie')
            p.import_auth_cookie()

        if op == Operation.LIST_CHANNELS:
            logging.info('Fetching channel list...')
            for chan in p.get_channel_list():
                print(chan)
        elif op == Operation.AUTHENTICATE:
            logging.info('Authenticating...')
            p.authenticate(username, password)
        else:
            if len(args) != 1:
                usage()

            logging.info('Getting stream information (%s)...' % args[0])
            info = p.get_stream_info(args[0])
            logging.info(':: Title: %s' % info['title'])

            if op == Operation.LIST_ALTERNATIVES:
                for i, alt in enumerate(info['alt']):
                    print('  #%d: ' % i, alt)
                sys.exit(0)

            logging.info('Creating A/V source (%d)' % alternative)
            source = p.get_av_source(info, alternative)

            sinkCmdline += ['-']
            sink = subprocess.Popen(sinkCmdline, stdin=subprocess.PIPE)
            while True:
                startTime = time.perf_counter()
                retry = source.run(sink)
                endTime = time.perf_counter()

                if not retry or (endTime - startTime) < _AVSOURCE_RETRY_THRESHOLD:
                    break
                logging.info('A/V source died prematurely; retrying...')
                info = p.get_stream_info(args[0])
                source = p.get_av_source(info, alternative)
    except (ValueError, RuntimeError) as err:
        print(err)

if __name__ == '__main__':
    main()
