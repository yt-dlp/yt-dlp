from collections import defaultdict


class Indirect:
    def __init__(self, initial, /):
        self.value = initial

    def __repr__(self, /):
        return f'{type(self).__name__}({self.value!r})'


# Internal only - no backwards compatibility guaranteed
postprocessors = Indirect({})
extractors = Indirect({})
IN_CLI = Indirect(False)
# `False`=force, `None`=disabled, `True`=enabled
LAZY_EXTRACTORS = Indirect(False)


# Plugins

plugin_specs = Indirect({})

# Whether plugins have been loaded once
all_plugins_loaded = Indirect(False)

plugins_enabled = Indirect(True)

plugin_dirs = Indirect(['external'])
plugin_ies = Indirect({})
plugin_overrides = Indirect(defaultdict(list))
plugin_pps = Indirect({})
