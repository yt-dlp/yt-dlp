from collections.abc import MutableMapping

from yt_dlp.utils import try_call


class LazyInfoDict(MutableMapping):
    def __init__(self, data=None, lazy=None):
        self._data = data or {}
        self._lazy = lazy or {}

        for key in self._data.keys() & self._lazy.keys():
            del self._lazy[key]

        self._data.update(dict.fromkeys(self._lazy.keys()))

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        if key in self._lazy:
            compute_func = self._lazy[key]

            print(f"Evaluating key {key!r}")
            updates = try_call(compute_func, expected_type=dict) or {}
            self._data.update(updates)
            for update in updates:
                self._lazy.pop(update, None)

        return self._data[key]

    def __setitem__(self, key, value):
        if key in self._lazy:
            del self._lazy[key]

        self._data[key] = value

    def __delitem__(self, key):
        if key in self._lazy:
            del self._lazy[key]

        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        data = f"{self._data!r}"
        if self._lazy:
            data += f", lazy={set(self._lazy.keys())!r}"
        return f"{type(self).__name__}({data})"


if __name__ == '__main__':
    def eval_test():
        print('eval_test')
        return {'test': 'test'}

    def eval_else():
        print('eval_else')
        return {'something': 'something', 'else': 'else'}

    data = LazyInfoDict({
        'nonlazy': 'nonlazy',
        'attribute': 'attribute',
    }, {
        'test': eval_test,
        'something': eval_else,
        'else': eval_else,
    })
    print(f'{data["else"]=}')
    print('-----')
    for key, value in data.items():
        print(f'data[{key!r}]={value!r}')
