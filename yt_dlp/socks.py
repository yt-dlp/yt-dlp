# Public Domain SOCKS proxy protocol implementation
# Adapted from https://gist.github.com/bluec0re/cafd3764412967417fd3
# References:
# SOCKS4 protocol http://www.openssh.com/txt/socks4.protocol
# SOCKS4A protocol http://www.openssh.com/txt/socks4a.protocol
# SOCKS5 protocol https://tools.ietf.org/html/rfc1928
# SOCKS5 username/password authentication https://tools.ietf.org/html/rfc1929

import collections
import socket

from .compat import compat_ord, compat_struct_pack, compat_struct_unpack

__author__ = 'Timo Schmid <coding@timoschmid.de>'

SOCKS4_VERSION = 4
SOCKS4_REPLY_VERSION = 0x00
# Excerpt from SOCKS4A protocol:
# if the client cannot resolve the destination host's domain name to find its
# IP address, it should set the first three bytes of DSTIP to NULL and the last
# byte to a non-zero value.
SOCKS4_DEFAULT_DSTIP = compat_struct_pack('!BBBB', 0, 0, 0, 0xFF)

SOCKS5_VERSION = 5
SOCKS5_USER_AUTH_VERSION = 0x01
SOCKS5_USER_AUTH_SUCCESS = 0x00


class Socks4Command:
    CMD_CONNECT = 0x01
    CMD_BIND = 0x02


class Socks5Command(Socks4Command):
    CMD_UDP_ASSOCIATE = 0x03


class Socks5Auth:
    AUTH_NONE = 0x00
    AUTH_GSSAPI = 0x01
    AUTH_USER_PASS = 0x02
    AUTH_NO_ACCEPTABLE = 0xFF  # For server response


class Socks5AddressType:
    ATYP_IPV4 = 0x01
    ATYP_DOMAINNAME = 0x03
    ATYP_IPV6 = 0x04


class ProxyError(socket.error):
    ERR_SUCCESS = 0x00

    def __init__(self, code=None, msg=None):
        if code is not None and msg is None:
            msg = self.CODES.get(code) or 'unknown error'
        super().__init__(code, msg)


class InvalidVersionError(ProxyError):
    def __init__(self, expected_version, got_version):
        msg = ('Invalid response version from server. Expected {:02x} got '
               '{:02x}'.format(expected_version, got_version))
        super().__init__(0, msg)


class Socks4Error(ProxyError):
    ERR_SUCCESS = 90

    CODES = {
        91: 'request rejected or failed',
        92: 'request rejected because SOCKS server cannot connect to identd on the client',
        93: 'request rejected because the client program and identd report different user-ids'
    }


class Socks5Error(ProxyError):
    ERR_GENERAL_FAILURE = 0x01

    CODES = {
        0x01: 'general SOCKS server failure',
        0x02: 'connection not allowed by ruleset',
        0x03: 'Network unreachable',
        0x04: 'Host unreachable',
        0x05: 'Connection refused',
        0x06: 'TTL expired',
        0x07: 'Command not supported',
        0x08: 'Address type not supported',
        0xFE: 'unknown username or invalid password',
        0xFF: 'all offered authentication methods were rejected'
    }


class ProxyType:
    SOCKS4 = 0
    SOCKS4A = 1
    SOCKS5 = 2


Proxy = collections.namedtuple('Proxy', (
    'type', 'host', 'port', 'username', 'password', 'remote_dns'))


class sockssocket(socket.socket):
    def __init__(self, *args, **kwargs):
        self._proxy = None
        super().__init__(*args, **kwargs)

    def setproxy(self, proxytype, addr, port, rdns=True, username=None, password=None):
        assert proxytype in (ProxyType.SOCKS4, ProxyType.SOCKS4A, ProxyType.SOCKS5)

        self._proxy = Proxy(proxytype, addr, port, username, password, rdns)

    def recvall(self, cnt):
        data = b''
        while len(data) < cnt:
            cur = self.recv(cnt - len(data))
            if not cur:
                raise EOFError(f'{cnt - len(data)} bytes missing')
            data += cur
        return data

    def _recv_bytes(self, cnt):
        data = self.recvall(cnt)
        return compat_struct_unpack(f'!{cnt}B', data)

    @staticmethod
    def _len_and_data(data):
        return compat_struct_pack('!B', len(data)) + data

    def _check_response_version(self, expected_version, got_version):
        if got_version != expected_version:
            self.close()
            raise InvalidVersionError(expected_version, got_version)

    def _resolve_address(self, destaddr, default, use_remote_dns):
        try:
            return socket.inet_aton(destaddr)
        except OSError:
            if use_remote_dns and self._proxy.remote_dns:
                return default
            else:
                return socket.inet_aton(socket.gethostbyname(destaddr))

    def _setup_socks4(self, address, is_4a=False):
        destaddr, port = address

        ipaddr = self._resolve_address(destaddr, SOCKS4_DEFAULT_DSTIP, use_remote_dns=is_4a)

        packet = compat_struct_pack('!BBH', SOCKS4_VERSION, Socks4Command.CMD_CONNECT, port) + ipaddr

        username = (self._proxy.username or '').encode()
        packet += username + b'\x00'

        if is_4a and self._proxy.remote_dns:
            packet += destaddr.encode() + b'\x00'

        self.sendall(packet)

        version, resp_code, dstport, dsthost = compat_struct_unpack('!BBHI', self.recvall(8))

        self._check_response_version(SOCKS4_REPLY_VERSION, version)

        if resp_code != Socks4Error.ERR_SUCCESS:
            self.close()
            raise Socks4Error(resp_code)

        return (dsthost, dstport)

    def _setup_socks4a(self, address):
        self._setup_socks4(address, is_4a=True)

    def _socks5_auth(self):
        packet = compat_struct_pack('!B', SOCKS5_VERSION)

        auth_methods = [Socks5Auth.AUTH_NONE]
        if self._proxy.username and self._proxy.password:
            auth_methods.append(Socks5Auth.AUTH_USER_PASS)

        packet += compat_struct_pack('!B', len(auth_methods))
        packet += compat_struct_pack(f'!{len(auth_methods)}B', *auth_methods)

        self.sendall(packet)

        version, method = self._recv_bytes(2)

        self._check_response_version(SOCKS5_VERSION, version)

        if method == Socks5Auth.AUTH_NO_ACCEPTABLE or (
                method == Socks5Auth.AUTH_USER_PASS and (not self._proxy.username or not self._proxy.password)):
            self.close()
            raise Socks5Error(Socks5Auth.AUTH_NO_ACCEPTABLE)

        if method == Socks5Auth.AUTH_USER_PASS:
            username = self._proxy.username.encode()
            password = self._proxy.password.encode()
            packet = compat_struct_pack('!B', SOCKS5_USER_AUTH_VERSION)
            packet += self._len_and_data(username) + self._len_and_data(password)
            self.sendall(packet)

            version, status = self._recv_bytes(2)

            self._check_response_version(SOCKS5_USER_AUTH_VERSION, version)

            if status != SOCKS5_USER_AUTH_SUCCESS:
                self.close()
                raise Socks5Error(Socks5Error.ERR_GENERAL_FAILURE)

    def _setup_socks5(self, address):
        destaddr, port = address

        ipaddr = self._resolve_address(destaddr, None, use_remote_dns=True)

        self._socks5_auth()

        reserved = 0
        packet = compat_struct_pack('!BBB', SOCKS5_VERSION, Socks5Command.CMD_CONNECT, reserved)
        if ipaddr is None:
            destaddr = destaddr.encode()
            packet += compat_struct_pack('!B', Socks5AddressType.ATYP_DOMAINNAME)
            packet += self._len_and_data(destaddr)
        else:
            packet += compat_struct_pack('!B', Socks5AddressType.ATYP_IPV4) + ipaddr
        packet += compat_struct_pack('!H', port)

        self.sendall(packet)

        version, status, reserved, atype = self._recv_bytes(4)

        self._check_response_version(SOCKS5_VERSION, version)

        if status != Socks5Error.ERR_SUCCESS:
            self.close()
            raise Socks5Error(status)

        if atype == Socks5AddressType.ATYP_IPV4:
            destaddr = self.recvall(4)
        elif atype == Socks5AddressType.ATYP_DOMAINNAME:
            alen = compat_ord(self.recv(1))
            destaddr = self.recvall(alen)
        elif atype == Socks5AddressType.ATYP_IPV6:
            destaddr = self.recvall(16)
        destport = compat_struct_unpack('!H', self.recvall(2))[0]

        return (destaddr, destport)

    def _make_proxy(self, connect_func, address):
        if not self._proxy:
            return connect_func(self, address)

        result = connect_func(self, (self._proxy.host, self._proxy.port))
        if result != 0 and result is not None:
            return result
        setup_funcs = {
            ProxyType.SOCKS4: self._setup_socks4,
            ProxyType.SOCKS4A: self._setup_socks4a,
            ProxyType.SOCKS5: self._setup_socks5,
        }
        setup_funcs[self._proxy.type](address)
        return result

    def connect(self, address):
        self._make_proxy(socket.socket.connect, address)

    def connect_ex(self, address):
        return self._make_proxy(socket.socket.connect_ex, address)
