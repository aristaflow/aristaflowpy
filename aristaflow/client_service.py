from typing import TypeVar, Type

from af_org_model_manager.api.global_security_manager_api import GlobalSecurityManagerApi
from af_org_model_manager.models.client_session_details import ClientSessionDetails

from .configuration import Configuration
from .rest_helper import RestPackageRegistry, RestPackage, RestPackageInstance


T = TypeVar('T')


class AristaFlowClientService(object):
    """Client Services for accessing the AristaFlow BPM platform
    """
    # the user session id this client service belongs to
    __user_session: str = None
    __rest_package_registry: RestPackageRegistry = None
    # package to package instance map
    __rest_packages: [RestPackage, RestPackageInstance] = None
    # cached service stubs
    __services: [type, object] = None
    # authentication
    __csd: ClientSessionDetails = None
    # the AristaFlow configuration
    __af_conf: Configuration = None

    def __init__(self, configuration: Configuration,
                 user_session: str,
                 rest_package_registry: RestPackageRegistry):
        self.__af_conf = configuration
        self.__user_session = user_session
        self.__rest_package_registry = rest_package_registry
        self.__rest_packages = {}
        self.__services = {}

    def get_service(self, service_type: Type[T]) -> T:
        """
        Returns a service instance for the given service type, e.g.
        get_service(InstanceControlApi)
        @param service_type The class of the requested service.
        """
        # return a cached instance
        if service_type in self.__services:
            return self.__services[service_type]

        # find the package description and package instance
        pkg = self.__rest_package_registry.get_rest_package(service_type)
        pkg_instance: RestPackageInstance = None
        if pkg in self.__rest_packages:
            pkg_instance = self.__rest_packages[pkg]
        else:
            pkg_instance = RestPackageInstance(pkg)

        # get the ApiClient object of the package
        api_client = pkg_instance.api_client
        # authentication data
        if self.__csd:
            self.__use_authentication(api_client)
        # instantiate the service
        service = service_type(api_client)
        # cache it
        self.__services[service_type] = service
        return service

    def __use_authentication(self, api_client: object):
        """Uses the client session details to set the default header
        """
        api_client.set_default_header("x-AF-Security-Token", self.__csd.token)

    @property
    def client_session_details(self) -> ClientSessionDetails:
        """ Returns the client session details of this service
        :return: The client session details of this service
        """
        return self.__csd

    @property
    def is_authenticated(self) -> bool:
        """ Returns true, if this client service is already authenticated
        """
        return self.__csd != None

    def authenticate(self, username: str, password: str, org_pos_id: int=None):
        """ Authenticates this client service and makes the authentication available to all __services.
        """
        if self.__csd != None:
            raise Exception("Already authenticated")

        csds: list[ClientSessionDetails] = None
        if org_pos_id != None:
            csds = self.get_service(GlobalSecurityManagerApi).authenticate_all(
                user_name=username, password=password, org_pos_id=org_pos_id, caller_uri=self.__af_conf.caller_uri)
        else:
            csds = self.get_service(GlobalSecurityManagerApi).authenticate_all(
                user_name=username, password=password, caller_uri=self.__af_conf.caller_uri)
        csd: ClientSessionDetails = None
        if len(csds) == 1:
            csd = csds[0]
        elif len(csds) == 0:
            raise Exception("User does not have an org position " +
                            username + " (supplied org position id: " + org_pos_id + ")")
        else:
            # pick the first as default
            csd = csds[0]
            # pick the one where username and org position name are the same
            for entry in csds:
                if entry.agent.agent.org_pos_name == entry.agent.agent.agent_name:
                    csd = entry
                    break

        # set the authentication for all ApiClient objects
        for _, inst in self.__rest_packages:
            self.__use_authentication(inst.api_client)

        self.__csd = csd
