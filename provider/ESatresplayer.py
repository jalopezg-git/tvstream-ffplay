import http.cookiejar, urllib.request, urllib.parse, json
import os.path, re
from common.avsource import CurlMpegtsSequenceMuxAVSource
from common.m3u import M3UPlaylist
from common.provider import ContentProvider

# Provider for [ES] Atresplayer (https://atresplayer.com/).  Atresplayer conforms to RFC 8216 for HTTP Live Streaming
class AtresplayerProvider(ContentProvider):
    _URL_AUTH = 'https://account.atresplayer.com/auth/v1/login'
    _URL_CHANNELS = 'https://api.atresplayer.com/client/v1/info/channels'
    _URL_STREAM_INFO = 'https://api.atresplayer.com/player/v1/live/%s'

    _DEFAULT_AUTH_COOKIE_FILE = os.path.join(os.path.expanduser('~'),
                                             '.atresplayer-cookie.txt')
    _DEFAULT_URLS_PER_PROC = 20

    def __init__(self, params={}):
        self.params = {
            'auth-cookie-file': self._DEFAULT_AUTH_COOKIE_FILE,
            'urls-per-proc': self._DEFAULT_URLS_PER_PROC,
        }
        self.params |= params

        self.cookieJar = http.cookiejar.MozillaCookieJar()
        self.http = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookieJar))
        if params.get('user-agent'):
            self.http.addHeader = [('User-agent', params['user-agent'])]

    def authenticate(self, username, password):
        # FIXME: this currently does not allow access to protected resources.
        # We might be missing something here (other than mismatching domain name?)
        data = urllib.parse.urlencode({'username': username,
                                       'password': password}).encode('ascii')
        # If authentication fails, this raises an exception due to HTTP status 403
        self.http.open(self._URL_AUTH, data)
        self.cookieJar.save(self.params['auth-cookie-file'])

    def import_auth_cookie(self):
        self.cookieJar.load(self.params['auth-cookie-file'])

    def get_channel_list(self):
        j = json.load(self.http.open(self._URL_CHANNELS))
        return {i['title']: {'id': i['id'],
                             'href': i['link']['href']} for i in j}

    def get_stream_info(self, resource):
        """ Get the information associated to a given resource.

        This comprises several steps: (i) fetch channel list; (ii) download
        stream information -contains title and URL of the `master.m3u8` playlist
        -; and (iii) download and parse `master.m3u8`.
        """
        if re.match('^https?://', resource):
            raise ValueError('Providing a URL is not currently supported')

        ls = self.get_channel_list()
        if not ls.get(resource):
            raise ValueError("'%s': no such entry in the channel list" % resource)

        j = json.load(self.http.open(self._URL_STREAM_INFO % ls[resource]['id']))
        master_m3u8 = j['sourcesLive'][0]['src']

        try:
            return {'title': j['titulo'],
                    'alt': M3UPlaylist(self.http.open(master_m3u8).read().decode('utf-8'),
                                       expectExtm3u=True),
                    '__prefix': master_m3u8.rpartition('/')[0] + '/'}
        except Exception:
            raise RuntimeError("Couldn't get stream information.  Did you forget to authenticate?")

    def parse_media_playlist(self, prefix, playlistUrl):
        """
        Parse a media playlist (RFC 8216) and return a tuple that holds the URL
        template and initial media sequence.  This tuple can be used to construct
        a CurlMpegtsSequenceAVSource.
        """
        ts = M3UPlaylist(self.http.open(playlistUrl).read().decode('utf-8'),
                         expectExtm3u=True)
        # Do not rely on the `EXT-X-MEDIA-SEQUENCE` attribute as it has been seen to carry incorrect
        # values; instead use the sequence number in the href string
        r = re.compile(r'-([0-9]+).ts')
        seq = re.search(r, ts[0]['href'])[1]
        return (prefix + re.sub(r, '-%s.ts', ts[0]['href']),
                int(seq))

    def collect_audio_playlists(self, masterPlaylist):
        """
        Collect all the audio playlists referenced in `masterPlaylist` and return a tuple containing
        `(audio_playlists, default_idx)`.
        `audio_playlists` is a list of dictionaries.  Each dictionary is the result of parsing the
        corresponding list of attributes in the master playlist; the `NAME` and `URI` keys refer to the
        name and the relative path of the playlist, respectively.
        """
        audio_playlists = []
        default = -1
        for entry in masterPlaylist:
            for k, v in entry['attrs']:
                if k == 'EXT-X-MEDIA':
                    attr_kv = M3UPlaylist.parse_kv_attr(v)
                    if attr_kv['TYPE'] == 'AUDIO':
                        if attr_kv['DEFAULT'] == 'YES':
                            default = len(audio_playlists)
                        audio_playlists += [attr_kv]
        return (audio_playlists, default)

    def get_mpegts_url(self, streamInfo, alternative):
        """ Get the base URL and current MPEG TS sequence number.  Specifically,
        this downloads and parses a `bitrate_xxx.m3u8` playlist.

        @param streamInfo Stream information, as returned by `get_stream_info()`
        @param alternative Alternative #.
        @return A dictionary that contains the required data to construct a
        CurlMpegtsSequenceMuxAVSource instance.
        """
        audio_playlists, audio_default = self.collect_audio_playlists(streamInfo['alt'])
        if audio_default == -1:
            logging.warning("Couldn't determine the default audio playlist; using 0")
            audio_default = 0

        prefix = streamInfo['__prefix']
        video = self.parse_media_playlist(prefix, prefix + streamInfo['alt'][alternative]['href'])
        audio = self.parse_media_playlist(prefix, prefix + audio_playlists[audio_default]['URI'])
        return [video, audio]

    def get_av_source(self, streamInfo, alternative=-1):
        urlTemplateAndInitSeq = self.get_mpegts_url(streamInfo, alternative)
        return CurlMpegtsSequenceMuxAVSource(urlTemplateAndInitSeq,
                                             int(self.params['urls-per-proc']),
                                             self.params['user-agent'],
                                             self.cookieJar)
