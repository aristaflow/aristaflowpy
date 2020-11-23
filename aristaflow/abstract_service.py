# -*- coding: utf-8 -*-
from aristaflow.service_provider import ServiceProvider
class AbstractService(object):
    ''' Abstract base class for service helpers
    '''

    _service_provider:ServiceProvider = None

    def __init__(self, service_provider:ServiceProvider):
        self._service_provider = service_provider
