from abc import abstractmethod

class ContentProvider:
    """ Abstract interface for content providers. """
    def __init__(self, params={}):
        """ Construct an instance of a content provider.

        @param params A dictionary of provider-specific parameters.  The
        `user-agent` key should be supported by all content providers using
        HTTP/HTTPS.
        """
        pass

    @abstractmethod
    def authenticate(self, username, password):
        """ Authenticate a user using the given credentials.  This should
        guarantee that the session cookie can be loaded in a different execution
        by calling `import_auth_cookie()`.

        An exception might be raised on authentication failure.

        @param username Username to use for authentication
        @param password Password
        """
        pass

    @abstractmethod
    def import_auth_cookie(self):
        """ Import an existing authentication cookie; see `authenticate()`. """
        pass

    @abstractmethod
    def get_channel_list(self):
        """ Get this list of live channels from this provider.

        @return A dictionary where keys correspond to channel names.  Values can
        be used to store provider-specific information.
        """
        pass

    @abstractmethod
    def get_stream_info(self, resource):
        """ Get the information associated to a given resource.

        @param resource The resource name, typically a channel name or a URL
        @return A dictionary that contains, at least, the `title` and `alt` keys
        (a list of alternatives, i.e. different codecs or video resolutions).
        The list of alternatives should be iterable.
        """
        pass

    @abstractmethod
    def get_av_source(self, streamInfo, alternative=-1):
        """ Get an AVSource instance for the given stream.

        @param streamInfo Stream information, as returned by `get_stream_info()`
        @param alternative Alternative #.
        @return An instance of an AVSource subclass
        """
        pass
