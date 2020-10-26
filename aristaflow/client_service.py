from typing import TypeVar, Type

from af_org_model_manager.api.global_security_manager_api import GlobalSecurityManagerApi
from af_org_model_manager.models.client_session_details import ClientSessionDetails

from .configuration import Configuration
#from .rest_helper import RestPackageRegistry, RestPackage, RestPackageInstance
from .worklist_service import WorklistService
from aristaflow.service_provider import ServiceProvider
from af_org_model_manager.models.authentication_data import AuthenticationData
from af_org_model_manager.models.auth_data_org_pos import AuthDataOrgPos
from af_org_model_manager.models.auth_data_user_name import AuthDataUserName
from af_org_model_manager.models.auth_data_arbitrary import AuthDataArbitrary
import base64


T = TypeVar('T')


class AristaFlowClientService(object):
    """Client Services for accessing the AristaFlow BPM platform
    """
    # the user session id this client service belongs to
    __user_session: str = None
    # authentication
    __csd: ClientSessionDetails = None
    # the AristaFlow configuration
    __af_conf: Configuration = None
    __service_provider:ServiceProvider = None
    __worklist_service:WorklistService = None

    def __init__(self, configuration: Configuration,
                 user_session: str,
                 service_provider:ServiceProvider):
        self.__af_conf = configuration
        self.__user_session = user_session
        self.__service_provider = service_provider

    def get_service(self, service_type: Type[T]) -> T:
        """
        Returns a service instance for the given service type, e.g.
        get_service(InstanceControlApi)
        @param service_type The class of the requested service.
        """
        return self.__service_provider.get_service(service_type)

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

    def authenticate_psk(self, username: str, org_pos_id: int=None):
        if self.__af_conf.pre_shared_key == None:
            raise Exception('Authentication mechanism unavailable')
        
        auth_data:list[AuthenticationData] = []
        if org_pos_id != None:
            auth_data.append(AuthDataOrgPos(org_pos_id, sub_class="AuthDataOrgPos"))
        auth_data.append(AuthDataUserName(username, sub_class="AuthDataUserName"))
        psk = self.__af_conf.pre_shared_key
        # get the utf-8 bytes, encode them using base 64 and decode the resulting bytes using ASCII
        psk_encoded = base64.b64encode(bytes(psk, "UTF-8")).decode('ascii')
        auth_data.append(AuthDataArbitrary(data=psk_encoded, sub_class="AuthDataArbitrary"))
        
        gsm: GlobalSecurityManagerApi = self.get_service(
            GlobalSecurityManagerApi)
        csds: list[ClientSessionDetails] = gsm.authenticate_all_method('SHARED_UTF-8_KEY', self.__af_conf.caller_uri,
                                                                       body=auth_data)

        self.__post_auth(csds, username, org_pos_id)


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

        self.__post_auth(csds, username, org_pos_id)


    def __post_auth(self, csds:list, username:str, org_pos_id:int):
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

        self.__service_provider.authenticated(csd)
        self.__csd = csd


    @property
    def worklist_service(self):
        if self.__worklist_service == None:
            self.__worklist_service = WorklistService(self)
        return self.__worklist_service
    
