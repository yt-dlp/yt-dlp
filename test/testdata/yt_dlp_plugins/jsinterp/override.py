from yt_dlp.jsinterp._deno import DenoJSI


class OverrideDenoJSI(DenoJSI, plugin_name='override'):
    TEST_FIELD = 'override'
