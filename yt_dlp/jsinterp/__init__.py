# flake8: noqa: F401
from .native import JSInterpreter
from .common import _JSI_PREFERENCES, JSIWrapper
from ._phantomjs import PhantomJSJSI, PhantomJSwrapper
from ._deno import DenoJSI, DenoJSDomJSI
from ..globals import jsi_runtimes, plugin_jsis
from ..plugins import PluginSpec, register_plugin_spec

jsi_runtimes.value.update({
    name: value
    for name, value in globals().items()
    if name.endswith('JSI')
})

plugin_spec = PluginSpec(
    module_name='jsinterp',
    suffix='JSI',
    destination=jsi_runtimes,
    plugin_destination=plugin_jsis,
)
register_plugin_spec(plugin_spec)

__all__ = [
    JSInterpreter,
    PhantomJSwrapper,
    _JSI_PREFERENCES,
    JSIWrapper,
]
