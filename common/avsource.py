import subprocess
import logging
import shlex
from abc import abstractmethod

class AVSource:
    """ Abstract interface for A/V sources """
    @abstractmethod
    def run(self, sink):
        """ Run the A/V source until sink terminates.

        @param sink An instance of the subprocess.Popen class.
        """
        pass

class CurlMpegtsSequenceAVSource(AVSource):
    """ An A/V source that uses `curl` to fetch a sequence of MPEG Transport
    Streams.  This class spawns a curl process for a batch of MPEG TS URLs and
    the stdout is piped to the sink's stdin.  On process termination, a new
    process is spawned reusing the same pipe, e.g.

      src = CurlMpegtsSequenceAVSource("https://site.org/mpegts/%s.ts", 1000, 2)

    the command line for the first two spawned processes is
    ```
    curl https://site.org/mpegts/1000.ts https://site.org/mpegts/1001.ts
    curl https://site.org/mpegts/1002.ts https://site.org/mpegts/1003.ts
    ```
    """
    def __init__(self, urlTemplate, startAt, urlsPerProc, userAgent=None, cookies=[]):
        """ Constructs a CurlMpegtsSequenceAVSource.

        @param urlTemplate The template to use for URL generation, e.g. `https://domain.tld/path/to/resource/%s.ts`
        @param startAt Sequence number to use in the first URL
        @param urlsPerProc Number of URLs per `curl` process
        @param userAgent Value for the `User-agent` HTTP header
        @param cookies An array of http.cookiejar.Cookie instances
        """
        self.urlTemplate = urlTemplate
        self.startAt = startAt
        self.urlsPerProc = urlsPerProc
        self.addHeaders = []
        if userAgent:
            self.addHeaders += ['-H', 'User-agent: %s' % userAgent]
        if cookies:
            self.addHeaders += ['-H', 'Cookie: %s' % '; '.join(map(
                                lambda c: c.name + '=' + c.value, cookies))]

    def run(self, sink):
        while True:
            argv = ['curl', '--silent', '--fail-early']
            argv += self.addHeaders
            argv += [self.urlTemplate % i for i in range(self.startAt,
                                                         self.startAt + self.urlsPerProc)]

            logging.debug('Spawning process: ' + shlex.join(argv))
            curl = subprocess.Popen(argv, stdout=sink.stdin)
            if curl.wait() != 0:
                break
            self.startAt += self.urlsPerProc
