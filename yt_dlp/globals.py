import os
from collections import defaultdict

# Please Note: Due to necessary changes and the complex nature involved in the plugin/globals system,
# no backwards compatibility is guaranteed for the plugin system API.
# However, we will still try our best.


class Indirect:
    def __init__(self, initial, /):
        self.value = initial

    def __repr__(self, /):
        return f'{type(self).__name__}({self.value!r})'


postprocessors = Indirect({})
extractors = Indirect({})

# Plugins
all_plugins_loaded = Indirect(False)
plugin_specs = Indirect({})
plugin_dirs = Indirect(['default'])

plugin_ies = Indirect({})
plugin_pps = Indirect({})
plugin_ies_overrides = Indirect(defaultdict(list))

# Misc
IN_CLI = Indirect(False)
LAZY_EXTRACTORS = Indirect(None)  # `False`=force, `None`=disabled, `True`=enabled
WINDOWS_VT_MODE = Indirect(False if os.name == 'nt' else None)
