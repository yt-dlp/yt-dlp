from yt_dlp.jsinterp._deno import DenoJSI


class _UnderscoreOverrideDenoJSI(DenoJSI, plugin_name='underscore-override'):
    SECONDARY_TEST_FIELD = 'underscore-override'
