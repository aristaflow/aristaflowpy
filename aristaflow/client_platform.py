# Default Python Libraries
import asyncio
from asyncio.base_events import BaseEventLoop
from multiprocessing.pool import ThreadPool

from .client_service import AristaFlowClientService
from .configuration import Configuration
from .rest_helper import RestPackageRegistry
from .service_provider import ServiceProvider


class AristaFlowClientPlatform(object):
    """Entry point to the AristaFlow Python Client framework."""

    # thread pool for async requests
    __async_thread_pool: ThreadPool = None
    __push_event_loop: BaseEventLoop = None

    def __init__(self, configuration: Configuration):
        self.configuration = configuration
        self.__client_services: [str, AristaFlowClientService] = {}
        self.__rest_package_registry = RestPackageRegistry(configuration)
        self.__async_thread_pool = ThreadPool(configuration.async_thread_pool_size)
        self.__push_event_loop = asyncio.new_event_loop()
        self.__async_thread_pool.apply_async(self._start_event_loop)

    def get_client_service(self, user_session: str = "python_default_session"):
        """
        :return: AristaFlowClientService The client service for the given user session
        """
        if user_session in self.__client_services:
            return self.__client_services[user_session]
        cs = AristaFlowClientService(
            self.configuration,
            user_session,
            ServiceProvider(
                self.__rest_package_registry, self.__async_thread_pool, self.__push_event_loop
            ),
        )
        self.__client_services[user_session] = cs
        return cs

    def _start_event_loop(self):
        """
        Starts the asyncio event loop for handling push notifications
        """
        try:
            asyncio.set_event_loop(self.__push_event_loop)
            self.__push_event_loop.run_forever()
        finally:
            self.__push_event_loop.close()
