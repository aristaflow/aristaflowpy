# -*- coding: utf-8 -*-
# Default Python Libraries
from typing import List, Union

# AristaFlow REST Libraries
from af_execution_manager.api.instance_control_api import InstanceControlApi
from af_execution_manager.api.templ_ref_remote_iterator_rest_api import (
    TemplRefRemoteIteratorRestApi,
)
from af_execution_manager.models.data_container import DataContainer
from af_execution_manager.models.instance_creation_data import InstanceCreationData
from af_execution_manager.models.instance_creation_rest_data import InstanceCreationRestData
from af_execution_manager.models.parameter_value import ParameterValue
from af_execution_manager.models.templ_ref_initial_remote_iterator_data import (
    TemplRefInitialRemoteIteratorData,
)
from af_execution_manager.models.templ_ref_remote_iterator_data import TemplRefRemoteIteratorData
from af_execution_manager.models.template_reference import TemplateReference
from af_process_manager.api.instance_manager_api import InstanceManagerApi
from af_process_manager.models.instance_reference import InstanceReference
from aristaflow.abstract_service import AbstractService
from aristaflow.utils import VERSION


class ProcessService(AbstractService):
    """Process related methods"""

    def __tpl_version_key(self, tpl: TemplateReference) -> int:
        return VERSION.key(tpl.version)

    def get_instantiable_template_by_type(self, process_type: str) -> TemplateReference:
        """Finds the first instantiable template of the given process Type"""
        tpls = self.get_instantiable_templates()
        tpls_of_type = []
        for tpl in tpls:
            if tpl.process_type == process_type:
                tpls_of_type += [tpl]
        # empty result

        if len(tpls_of_type) == 0:
            return None
        # reverse sort by version
        tpls_of_type = sorted(tpls_of_type, key=self.__tpl_version_key, reverse=True)
        # return first entry
        return tpls_of_type[0]

    def get_instantiable_templates(self) -> List[TemplateReference]:
        """Retrieves the instantiable tempaltes from the server
        :return: List[TemplateReference] The instantiable templates for the current user
        """
        ic: InstanceControlApi = self._service_provider.get_service(InstanceControlApi)
        initial: TemplRefInitialRemoteIteratorData = ic.get_instantiable_templ_refs()
        tpls: List[TemplateReference] = []
        self.__iterate(tpls, initial)
        return tpls

    def __iterate(
        self,
        tpls: List[TemplateReference],
        inc: Union[TemplRefInitialRemoteIteratorData, TemplRefRemoteIteratorData],
    ):
        """Consumes an template reference remote iterator until it is used up
        @param tpls The tpls list to fill with the template references
        @param inc The first or next iteration to consume and append to tpls.
        """
        if inc is None:
            return
        # append the tpls
        if inc.templ_refs:
            tpls += inc.templ_refs
        else:
            return
        # iterator is used up
        if inc.dropped:
            return

        # fetch next
        tref_rest: TemplRefRemoteIteratorRestApi = self._service_provider.get_service(
            TemplRefRemoteIteratorRestApi
        )
        next_it: TemplRefRemoteIteratorData = tref_rest.templ_ref_get_next(inc.iterator_id)
        self.__iterate(tpls, next_it)

    def start_by_type(
        self, process_type: str, callback_uri: str = None, input_data: dict = None
    ) -> str:
        """Starts the newest version of the given process type, returns the logical ID of the started instance."""
        tpl = self.get_instantiable_template_by_type(process_type)
        if tpl is None:
            raise Exception("Unknown process type: " + process_type)
        return self.start_by_id(tpl.id, callback_uri, input_data)

    def start_by_id(
        self, template_id: str, callback_uri: str = None, input_data: dict = None
    ) -> str:
        """Starts a process given by the template id. Returns the logical ID of the started instance."""
        ic: InstanceControlApi = self._service_provider.get_service(InstanceControlApi)
        if callback_uri is None:
            inst_creation_data = InstanceCreationData(sub_class="InstanceCreationData")
            inst_creation_data.dc = self.__create_instance_container(ic, template_id, input_data)
            return ic.create_and_start_instance(template_id, body=inst_creation_data)
        else:
            inst_creation_data = InstanceCreationRestData(
                sub_class="InstanceCreationRestData", notification_callback=callback_uri
            )
            inst_creation_data.dc = self.__create_instance_container(ic, template_id, input_data)
            return ic.create_and_start_instance_callback(
                body=inst_creation_data, templ_id=template_id
            )

    def __create_instance_container(
        self, ic: InstanceControlApi, template_id: str, input_data: dict
    ) -> DataContainer:
        """Creates an instance data container for the given template, if required"""
        idc = None
        if input_data is not None and len(input_data) != 0:
            idc = ic.create_instance_data_container(template_id)
            pv: ParameterValue = None
            for pv in idc.values:
                if pv.name in input_data:
                    value = input_data[pv.name]
                    pv.value = value
        return idc

    def get_instance_ref(self, inst_id: str) -> InstanceReference:
        """
        Finds the instance reference for the given instance ID (logical or log ID)
        """
        im: InstanceManagerApi = self._service_provider.get_service(InstanceManagerApi)
        try:
            return im.get_instance_refs(body=[inst_id]).inst_refs[0]
        except Exception:
            logicl_id = im.get_logical_instance_ids(body=[inst_id]).inst_ids[0]
            return im.get_instance_refs(body=[logicl_id]).inst_refs[0]
