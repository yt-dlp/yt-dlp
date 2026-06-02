class SimpleSignal:
    def __init__(self):
        self._subscribers = []

    def connect(self, callback):
        self._subscribers.append(callback)

    def emit(self, *args):
        for callback in list(self._subscribers):
            callback(*args)


try:
    from PySide6.QtCore import QObject, QThread, Signal
except ImportError:
    QObject = object

    class QThread:
        def start(self):
            self.run()

        def run(self):
            pass

    class Signal:
        def __init__(self, *_args):
            self._name = None

        def __set_name__(self, _owner, name):
            self._name = f"_{name}_signal"

        def __get__(self, instance, _owner):
            if instance is None:
                return self
            signal = instance.__dict__.get(self._name)
            if signal is None:
                signal = SimpleSignal()
                instance.__dict__[self._name] = signal
            return signal
