"""PUBLIC API"""


def sig_spec_id(example_sig):
    """ Return a string representation of a signature """
    return '.'.join(str(len(part)) for part in example_sig.split('.'))


def solve_sig(s, spec):
    return ''.join(s[i] for i in spec)
