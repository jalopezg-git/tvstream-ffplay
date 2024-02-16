import logging
import os
import shlex
import subprocess
from abc import abstractmethod
from threading import Thread

class AVSource:
    """ Abstract interface for A/V sources """
    @abstractmethod
    def run(self, sink):
        """ Run the A/V source until sink terminates.

        @param sink An instance of the subprocess.Popen class.
        @return `True` if the operation should be retried (if possible); `False` otherwise
        """
        pass

class CurlMpegtsSequenceAVSource(AVSource):
    """ An A/V source that uses `curl` to fetch a sequence of MPEG Transport
    Streams.  This class spawns a curl process for a batch of MPEG TS URLs and
    the stdout is piped to the sink's stdin.  On process termination, a new
    process is spawned reusing the same pipe, e.g.

      src = CurlMpegtsSequenceAVSource(("https://site.org/mpegts/%s.ts", 1000), 2)

    the command line for the first two spawned processes is
    ```
    curl https://site.org/mpegts/1000.ts https://site.org/mpegts/1001.ts
    curl https://site.org/mpegts/1002.ts https://site.org/mpegts/1003.ts
    ```
    """
    def __init__(self, urlTemplateAndInitSeq, urlsPerProc, userAgent=None, cookies=[]):
        """ Constructs a CurlMpegtsSequenceAVSource.

        @param urlTemplateAndInitSeq A tuple that holds the template to use for URL generation, e.g.
        `https://domain.tld/path/to/resource/%s.ts` and the sequence number to use in the first URL
        @param urlsPerProc Number of URLs per `curl` process
        @param userAgent Value for the `User-agent` HTTP header
        @param cookies An array of http.cookiejar.Cookie instances
        """
        self.urlTemplateAndInitSeq = urlTemplateAndInitSeq
        self.urlsPerProc = urlsPerProc
        self.addHeaders = []
        if userAgent:
            self.addHeaders += ['-H', 'User-agent: %s' % userAgent]
        if cookies:
            self.addHeaders += ['-H', 'Cookie: %s' % '; '.join(map(
                                lambda c: c.name + '=' + c.value, cookies))]

    def curl_loop(curlArgv, urlTemplate, startAt, urlsPerProc, fhStdout):
        while True:
            argv = curlArgv + [urlTemplate % i for i in range(startAt, startAt + urlsPerProc)]
            startAt += urlsPerProc

            logging.debug('Spawning process: ' + shlex.join(argv))
            curl = subprocess.Popen(argv, stdout=fhStdout)
            if curl.wait() != 0:
                return

    def run(self, sink):
        CurlMpegtsSequenceAVSource.curl_loop(['curl', '--silent', '--fail', '--fail-early'] + self.addHeaders,
                                             *self.urlTemplateAndInitSeq, self.urlsPerProc, sink.stdin)
        return sink.poll() == None

class CurlMpegtsSequenceMuxAVSource(CurlMpegtsSequenceAVSource):
    """ An A/V source that spawns different `curl` processes to separately fetch
    the video and audio data.  An extra `ffmpeg` process is used to multiplex
    both streams before feeding it to the sink.

    In contrast to `CurlMpegtsSequenceAVSource`, the constructor takes an array of template URLs
    and initial sequence numbers; an extra `curl` process is spawned for each element in the array.
    ```
    """
    def run(self, sink):
        threads = []
        pipes = []
        argv_ffmpeg_input = []
        for T in self.urlTemplateAndInitSeq:
            pipes += [os.pipe()]
            argv_ffmpeg_input += ['-i', ('pipe:%i' % pipes[-1][0])]
            curl_fhStdout = os.fdopen(pipes[-1][1], 'wb', buffering=0)
            threads += [Thread(target=CurlMpegtsSequenceAVSource.curl_loop,
                               args=[['curl', '--silent', '--fail', '--fail-early'] + self.addHeaders,
                                     *T, self.urlsPerProc, curl_fhStdout])]
            threads[-1].start()

        mux = subprocess.Popen(['ffmpeg', '-loglevel', 'quiet',
                                '-c:v', 'copy', '-c:a', 'copy', '-f', 'mpegts', '-'] + argv_ffmpeg_input,
                               stdout=sink.stdin, pass_fds=[p[0] for p in pipes])

        # Close unused read end of the pipes
        for p in pipes:
            os.close(p[0])
        return mux.wait() != 0 and sink.poll() == None
