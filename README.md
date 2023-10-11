# tvstream-ffplay - Play streamed content from the console via ffmpeg
`tvstream-ffplay.py` is a Python script that allows users to watch TV channels
or other streamed content via `ffplay` (part of the ffmpeg package).  This is
especially useful for low-power computers, e.g. Raspberry Pi, in which the
browsing experience is somewhat limited.  Many of these devices support video
decoding on the GPU but this capability is not always usable in the web browser.
Such is the case of the `chromium` package provided by ArchLinux ARM on the
Raspberry Pi, that was not patched to leverage MMAL video decoding.

Note that although `ffplay` is the default sink, any video player capable of
consuming data on stdin should work, e.g. vlc.

Currently, the only supported provider is ATRESplayer (ES - Atresmedia). There
is work in progress to support other content providers.

![ATRESMEDIA holds the rights of the image shown in the `ffplay` window](https://github.com/jalopezg-git/tvstream-ffplay/assets/36541918/c049469e-05d5-43d0-9071-58fff4dabc4c)

(The screenshot above is for demonstration purposes; ATRESMEDIA holds the rights of the image shown in the `ffplay` window above.)

## Dependencies
This script depends on the `ffmpeg` and `curl` packages.  Chances are that those
are already installed on your system; if not, most certainly they should be
provided by your distribution.  For instructions, refer to the package manager
manual page, e.g. to install them on ArchLinux:
```
$ sudo pacman -Sy ffmpeg curl
```

## Usage
```
Usage: ./tvstream-ffplay.py [OPTION]... RESOURCE

RESOURCE is either a channel name from the channel list or an URL.

OPTION can be one of:
  -h, --help              Show this usage message
  --log-level=N           Change the log level to N (10=debug 20=info 30=warning 40=error 50=critical)

  --param='KEY=VALUE'     Pass an additional parameter to a provider
  --list-providers        List the available providers
  -p, --provider=PRV      Use PRV as provider; default is `AtresplayerProvider'
  -l, --list-channels     List available live channels

  -s, --sink=SINKCMD      Set SINKCMD as the sink; default is `ffplay'
  --sink-args=ARGS        Additional arguments for the sink command

  --authenticate-as=USER  Authenticate as USER and save the authentication cookie
  --password=PASSWD       Use PASSWD for authentication (used with --authenticate-as=)
  --use-auth-cookie       Use saved authentication cookie for this request (see also --authenticate-as=)

  --list-alternatives     List available alternatives for the requested resource
  --alternative=N         Request alternative N


Examples:
  $ ./tvstream-ffplay.py --list-channels
  $ ./tvstream-ffplay.py --list-alternatives 'Antena 3'
  $ ./tvstream-ffplay.py --sink-args='-vcodec h264_mmal -fs' --alternative=2 'laSexta'
  $ ./tvstream-ffplay.py --param='urls-per-proc=30' 'Antena 3'
```

## Contribute
You can contribute to this project making a pull-request.  Also, if you find a
bug, please fill in an issue [here](https://github.com/jal0p3zg/tvstream-ffplay/issues).
