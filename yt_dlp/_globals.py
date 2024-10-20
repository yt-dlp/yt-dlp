from collections import defaultdict
from contextvars import ContextVar

# Internal only - no backwards compatibility guaranteed

postprocessors = ContextVar('postprocessors', default={})
extractors = ContextVar('extractors', default={})
IN_CLI = ContextVar('IN_CLI', default=False)
# `False`=force, `None`=disabled, `True`=enabled
LAZY_EXTRACTORS = ContextVar('LAZY_EXTRACTORS', default=False)


# Plugins

plugin_specs = ContextVar('plugin_specs', default={})

# Whether plugins have been loaded once
all_plugins_loaded = ContextVar('all_plugins_loaded', default=False)

plugins_enabled = ContextVar('plugins_enabled', default=True)

plugin_dirs = ContextVar('plugin_dirs', default=('external', ))
plugin_ies = ContextVar('plugin_ies', default={})
plugin_overrides = ContextVar('plugin_overrides', default=defaultdict(list))
plugin_pps = ContextVar('plugin_pps', default={})
