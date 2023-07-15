import http.client
import socket
import ssl
import urllib.error

network_exceptions = [urllib.error.URLError, http.client.HTTPException, socket.error]
if hasattr(ssl, 'CertificateError'):
    network_exceptions.append(ssl.CertificateError)
network_exceptions = tuple(network_exceptions)
