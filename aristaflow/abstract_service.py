# -*- coding: utf-8 -*-
# AristaFlow REST Libraries
import logging
import socket

from sseclient import SSEClient

from aristaflow.remote_iterator_handler import RemoteIteratorHandler
from aristaflow.service_provider import ServiceProvider


class AbstractService(object):
    """Abstract base class for service helpers"""

    _service_provider: ServiceProvider = None
    _rem_iter_handler: RemoteIteratorHandler = None
    _disconnected: bool = False

    def __init__(self, service_provider: ServiceProvider):
        self._service_provider = service_provider
        self._rem_iter_handler = RemoteIteratorHandler(service_provider)

    def disconnect(self):
        """ Called when the service should disconnect any open connection from the backend. """
        self._disconnected = True

    def _close_sse_client(self, sse_client:SSEClient):
        """ Helper method to close the sse_client connection. """
        if sse_client is not None:
            try:
                if sse_client.resp.raw._fp is not None:
                    raw_sock = sse_client.resp.raw._fp.fp.raw
                    if hasattr(raw_sock, '_sock'):
                        raw_sock = raw_sock._sock
                    if hasattr(raw_sock, 'shutdown'):
                        raw_sock.shutdown(socket.SHUT_RDWR)
                    raw_sock.close()
            except Exception as e:
                logging.warning('Exception while closing the SSEClient ', e)
