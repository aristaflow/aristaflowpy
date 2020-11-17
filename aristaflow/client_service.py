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
from af_org_model_manager.models.auth_data_app_name import AuthDataAppName
from af_org_model_manager.models.auth_data_password import AuthDataPassword
from af_org_model_manager.models.qualified_agent import QualifiedAgent
from af_worklist_manager.models.worklist_item import WorklistItem
from af_remote_html_runtime_manager.api.runtime_manager_api import RuntimeManagerApi
from af_remote_html_runtime_manager.api.synchronous_activity_starting_api import SynchronousActivityStartingApi
from af_remote_html_runtime_manager.models.gui_context import GuiContext
from af_remote_html_runtime_manager.models.ebp_instance_reference import EbpInstanceReference
from af_worklist_manager.models.af_activity_reference import AfActivityReference
from aristaflow.html_gui_context import HtmlGuiContext
from af_execution_manager.api.activity_execution_control_api import ActivityExecutionControlApi
import af_execution_manager
from af_remote_html_runtime_manager.models.activity_rest_callback_data import ActivityRestCallbackData
from aristaflow.process_service import ProcessService


T = TypeVar('T')
D = TypeVar('D')


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
    __is_html_runtime_manager_logged_on = False
    __process_service:ProcessService = None

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

    def authenticate(self, username: str, password: str = None, org_pos_id: int=None):
        if self.__csd != None:
            raise Exception("Already authenticated")
        
        auth_data:list[AuthenticationData] = []
        auth_data.append(AuthDataUserName(username, sub_class="AuthDataUserName"))
        if org_pos_id != None:
            auth_data.append(AuthDataOrgPos(org_pos_id, sub_class="AuthDataOrgPos"))
        psk = self.__af_conf.pre_shared_key
        method:str = None
        # if a password was provided, use it
        if password:
            auth_data.append(AuthDataPassword(password=password, sub_class="AuthDataPassword"))
            method = 'UTF-8_PASSWORD';
        # if PSK is configured, use that
        elif psk:
            # get the utf-8 bytes, encode them using base 64 and decode the resulting bytes using ASCII
            psk_encoded = base64.b64encode(bytes(psk, "UTF-8")).decode('ascii')
            auth_data.append(AuthDataArbitrary(data=psk_encoded, sub_class="AuthDataArbitrary"))
            method = 'SHARED_UTF-8_KEY'
        else:
            raise Exception('No authentication method left');
        
        gsm: GlobalSecurityManagerApi = self.get_service(
            GlobalSecurityManagerApi)

        # use a provided application name
        if self.__af_conf.application_name:
            if  org_pos_id == None:
                # if an application name is provided, an org position ID must be used as well
                # get the org positions
                agents:list[QualifiedAgent] = gsm.pre_authenticate_method(method, body=auth_data)
                agent:QualifiedAgent = None
                # pick the single org position
                if len(agents) == 1:
                    agent = agents[0]
                # none: can't login
                elif len(agents) == 0:
                    raise Exception(f"User does not have an org position {username} (supplied org position id: {org_pos_id})")
                else:
                    # use the first org position, except there is a agent_name/username match     
                    agent = agents[0]
                    for a in agents:
                        if a.agent_name == username:
                            agent = a
                            break
                # set the org position for the actual authentication
                auth_data.append(AuthDataOrgPos(agent.org_pos_id, sub_class='AuthDataOrgPos'))
            # use the application name
            auth_data.append(AuthDataAppName(app_name=self.__af_conf.application_name, sub_class="AuthDataAppName"))
        
        csds: list[ClientSessionDetails] = gsm.authenticate_all_method(method, self.__af_conf.caller_uri,
                                                                       body=auth_data)

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

    def is_html_activity(self, item:WorklistItem) -> bool:
        return item.act_ref.gui_context_id == 'HTMLContext' or item.act_ref.executable_component_name == 'de.aristaflow.form.Form' or item.act_ref.executable_component_name  == 'de.aristaflow.form.GeneratedForm'

    @property
    def worklist_service(self):
        if self.__worklist_service == None:
            self.__worklist_service = WorklistService(self.__service_provider)
        return self.__worklist_service

    @property
    def process_service(self):
        if self.__process_service == None:
            self.__process_service = ProcessService(self.__service_provider)
        return self.__process_service

    def start_html_activity(self, item:WorklistItem, callback_url:str):
        """
        Starts the given HTML GUI worklist item using the Remote HTML Runtime Manager
        """
        if item == None:
            raise Exception('No worklist item provided')
        # accept user form and HTMLContext based activities
        if not(self.is_html_activity(item)):
            raise Exception(f'Not an HTML activity: {item.act_ref.gui_context_id}')
        if item.state == 'STARTED':
            raise Exception('Item is already started')
        sas = self.get_html_activity_starting()
        gc:GuiContext = None
        ar:AfActivityReference = item.act_ref
        #print('Starting activity...')
        ebp_ir:EbpInstanceReference = EbpInstanceReference(ar.type, ar.instance_id, ar.instance_log_id, ar.base_template_id, ar.node_id, ar.node_iteration, ar.execution_manager_uris, ar.runtime_manager_uris)
        # "AVAILABLE", "ASSIGNED", "STARTED", "SUSPENDED", "ENQUIRED"
        if item.state == 'AVAILABLE' or item.state == 'ASSIGNED':
            if callback_url != None:
                cb_data = ActivityRestCallbackData(sub_class='ActivityRestCallbackData', notification_callback=callback_url, activity=ebp_ir)
                gc = sas.start_activity_callback(body=cb_data)
            else:
                gc = sas.start_activity(body=ebp_ir)
        else:
            if callback_url != None:
                cb_data = ActivityRestCallbackData(sub_class='ActivityRestCallbackData', notification_callback=callback_url, activity=ebp_ir)
                gc = sas.resume_activity_callback(body=cb_data)
            else:
                gc = sas.resume_activity(body=ebp_ir)
        return HtmlGuiContext(gc)
    
    
    def get_html_activity_starting(self) -> SynchronousActivityStartingApi:
        """
        Returns the Remote HTML Runtime Manager Syncrounous Activity Starting, ensuring logon to the Runtime Manager
        """
        sas:SynchronousActivityStartingApi = self.get_service(SynchronousActivityStartingApi)
        if self.__is_html_runtime_manager_logged_on:
            return sas
        rm:RuntimeManagerApi = self.get_service(RuntimeManagerApi)
        rm.logon(body=self.__csd)
        self.__is_html_runtime_manager_logged_on = True
        return sas
    
    def reset_activity(self, item:WorklistItem):
        """ Resets the given worklist item.
        """
        if item.state != 'STARTED':
            # nothing to do
            return
        # TODO check for a "local" activity for a soft reset
        ar:AfActivityReference = item.act_ref
        ebp_ir = af_execution_manager.EbpInstanceReference(ar.type, ar.instance_id, ar.instance_log_id, ar.base_template_id, ar.node_id, ar.node_iteration, ar.execution_manager_uris, ar.runtime_manager_uris)
        aec:ActivityExecutionControlApi = self.get_service(ActivityExecutionControlApi)
        aec.reset_to_prev_savepoint(body=ebp_ir, force=True)
        
    def deserialize(self, data, klass:Type[D]) -> D:
        """ Deserialize data using the given class of the generated OpenAPI models. 
        """
        return self.__service_provider.deserialize(data, klass)

    def serialize(self, obj) -> str:
        """ Serialize REST model object 
        """
        return self.__service_provider.serialize(obj)
    
    @property
    def autostart_timeout_seconds(self) -> int:
        """ Wait time in seconds for auto start signals
        """
        return self.__af_conf.autostart_timeout_seconds
