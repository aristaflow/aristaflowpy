from typing import List, Union

from aristaflow.service_provider import ServiceProvider
from af_execution_manager.api.instance_control_api import InstanceControlApi
from af_execution_manager.models.templ_ref_initial_remote_iterator_data import TemplRefInitialRemoteIteratorData
from af_execution_manager.api.templ_ref_remote_iterator_rest_api import TemplRefRemoteIteratorRestApi
from af_execution_manager.models.templ_ref_remote_iterator_data import TemplRefRemoteIteratorData
from af_execution_manager.models.template_reference import TemplateReference
from af_execution_manager.models.instance_creation_data import InstanceCreationData
from af_execution_manager.models.instance_creation_rest_data import InstanceCreationRestData
class ProcessService(object):
    """ Process related methods
    """

    __service_provider:ServiceProvider = None

    def __init__(self, service_provider:ServiceProvider):
        self.__service_provider = service_provider
    
    
    def get_instantiable_templyte_by_type(self, process_type:str) -> TemplateReference:
        """ Finds the first instantiable template of the given process Type
        """
        tpls = self.get_instantiable_templates()
        for tpl in tpls:
            if tpl.process_type == process_type:
                return tpl
        return None
    
    
    def get_instantiable_templates(self) -> List[TemplateReference]:
        """ Retrieves the instantiable tempaltes from the server
        :return: List[TemplateReference] The instantiable templates for the current user 
        """
        ic:InstanceControlApi = self.__service_provider.get_service(InstanceControlApi)
        initial:TemplRefInitialRemoteIteratorData = ic.get_instantiable_templ_refs()
        tpls: List[TemplateReference] = []
        self.__iterate(tpls, initial)
        return tpls
    
    def __iterate(self, tpls: List[TemplateReference], inc: Union[TemplRefInitialRemoteIteratorData, TemplRefRemoteIteratorData]):
        """ Consumes an template reference remote iterator until it is used up
        @param tpls The tpls list to fill with the template references
        @param inc The first or next iteration to consume and append to tpls. 
        """
        if inc == None:
            return
        # append the tpls
        if inc.templ_refs:
            tpls += inc.templ_refs
        # iterator is used up
        if inc.dropped:
            return

        # fetch next
        tref_rest: TemplRefRemoteIteratorRestApi = self.__service_provider.get_service(
            TemplRefRemoteIteratorRestApi)
        next_it: TemplRefRemoteIteratorData = tref_rest.templ_ref_get_next(inc.iterator_id)
        self.__iterate(tpls, next_it)


    def start_by_id(self, template_id:str, callback_uri:str = None) -> str:
        """ Starts a process given by the template id. Returns the logical ID of the started instance.
        """
        ic:InstanceControlApi = self.__service_provider.get_service(InstanceControlApi)
        if callback_uri == None:
            return ic.create_and_start_instance(template_id)
        else:
            inst_creation_data = InstanceCreationRestData(sub_class='InstanceCreationRestData', notification_callback=callback_uri)
            return ic.create_and_start_instance_callback(body=inst_creation_data, templ_id=template_id)
        
