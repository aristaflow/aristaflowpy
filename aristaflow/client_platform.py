from .client_service import AristaFlowClientService
from .configuration import Configuration
from .rest_helper import RestPackageRegistry


class AristaFlowClientPlatform(object):
    """ Entry point to the AristaFlow Python Client framework.
    """

    def __init__(self, configuration: Configuration):
        self.configuration = configuration
        self.__client_services: [str, AristaFlowClientService] = {}
        self.__rest_package_registry = RestPackageRegistry(configuration)

    def get_client_service(self, user_session: str="python_default_session"):
        """
        :return: AristaFlowClientService The client service for the given user session
        """
        if user_session in self.__client_services:
            return self.__client_services[user_session]
        cs = AristaFlowClientService(
            self.configuration, user_session, self.__rest_package_registry)
        self.__client_services[user_session] = cs
        return cs
