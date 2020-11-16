from . import AristaFlowClientService
from . import Configuration
from .rest_helper import RestPackageRegistry
from aristaflow.service_provider import ServiceProvider
from multiprocessing.pool import ThreadPool


class AristaFlowClientPlatform(object):
    """ Entry point to the AristaFlow Python Client framework.
    """

    # thread pool for async requests
    __async_thread_pool:ThreadPool = None

    def __init__(self, configuration: Configuration):
        self.configuration = configuration
        self.__client_services: [str, AristaFlowClientService] = {}
        self.__rest_package_registry = RestPackageRegistry(configuration)
        self.__async_thread_pool = ThreadPool(configuration.async_thread_pool_size)

    def get_client_service(self, user_session: str="python_default_session"):
        """
        :return: AristaFlowClientService The client service for the given user session
        """
        if user_session in self.__client_services:
            return self.__client_services[user_session]
        cs = AristaFlowClientService(
            self.configuration, user_session, ServiceProvider(self.__rest_package_registry, self.__async_thread_pool))
        self.__client_services[user_session] = cs
        return cs
