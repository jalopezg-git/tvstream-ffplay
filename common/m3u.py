import re

class M3UPlaylist:
    """ Simple M3U/EXTM3U playlist. Objects of this type partially implement the
    container interface, i.e. its elements may be accessed using `playlist[i]`.

    Each entry is a dictionary that contains two keys ('href' and 'attrs').
    'href' contains the location od the resource; 'attrs' is a dictionary of
    parsed EXTM3U attributes.
    """
    def __init__(self, content, expectExtm3u=False):
        """ Parses the given string as a [EXT]M3U playlist.

        @param content String to parse
        @param expectExtm3u If true, the `#EXTM3U` header is required
        """
        self.ents = []

        lines = content.splitlines()
        if not lines:
            return
        self.extm3u = lines[0] == '#EXTM3U'
        if self.extm3u:
            del lines[0]
        if expectExtm3u and not self.extm3u:
            raise ValueError("Expected #EXTM3U header")

        attrs = {}
        for line in lines:
            if not line:
                continue
            m = re.match('#([^:]+):?(.*)', line)
            if m:
                attrs[m[1]] = m[2].strip()
            else:
                self.ents += [{'href': line, 'attrs': attrs}]
                attrs = {}

    def __len__(self):
        return len(self.ents)

    def __getitem__(self, key):
        return self.ents[key]
