import importlib.resources


def load_script(filename, error_hook=None):
    if importlib.resources.is_resource(__package__, filename):
        try:
            return importlib.resources.read_text(__package__, filename)
        except (OSError, FileNotFoundError, ModuleNotFoundError) as e:
            if error_hook:
                error_hook(e)
            return None
    return None
