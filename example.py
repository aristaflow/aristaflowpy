# Default Python Libraries
from typing import List

# AristaFlow REST Libraries
from af_execution_manager.api.instance_control_api import InstanceControlApi
from af_execution_manager.models.templ_ref_initial_remote_iterator_data import (
    TemplRefInitialRemoteIteratorData,
)
from af_licence_manager.api.arista_flow_service_api import AristaFlowServiceApi
from af_licence_manager.api.licence_manager_api import LicenceManagerApi
from af_runtime_service.api.remote_activity_starting_api import RemoteActivityStartingApi
from af_runtime_service.api.remote_runtime_environment_api import RemoteRuntimeEnvironmentApi
from af_runtime_service.models.activity_configuration import ActivityConfiguration
from af_runtime_service.models.activity_instance import ActivityInstance
from af_runtime_service.models.data_context import DataContext
from af_runtime_service.models.ebp_instance_reference import EbpInstanceReference
from af_runtime_service.models.parameter_value import ParameterValue
from af_runtime_service.models.simple_session_context import SimpleSessionContext
from af_worklist_manager.models.af_activity_reference import AfActivityReference
from af_worklist_manager.models.worklist_item import WorklistItem
from aristaflow.client_platform import AristaFlowClientPlatform
from aristaflow.configuration import Configuration


conf = Configuration(
    base_url="http://127.0.0.1:8080/", caller_uri="http://localhost/python", application_name=None
)
platform = AristaFlowClientPlatform(conf)
cs = platform.get_client_service()
cs.authenticate("supervisor", "password")
# when PSK authentication is configured, no password is required
# cs.authenticate("supervisor")


def print_connection_info():
    lm: LicenceManagerApi = cs.get_service(LicenceManagerApi)
    afsa: AristaFlowServiceApi = cs.get_service(AristaFlowServiceApi)
    print(f"Connected to BPM platform version {afsa.get_release().version}")
    li = lm.get_licence_information()
    print(f"Licensed to: {li.licensee}")


print_connection_info()


def print_template_info():
    ic = cs.get_service(InstanceControlApi)
    tpl: TemplRefInitialRemoteIteratorData = ic.get_instantiable_templ_refs()
    print(f"Found instantiable templates: {len(tpl.templ_refs)}")


print_template_info()

ws = cs.worklist_service

items = ws.get_worklist()
print(f"Found {len(items)} worklist items")
ws.update_worklist()
print(f"Found {len(items)} worklist items")


def runtime_service_example(item: WorklistItem):
    # build an EbpInstanceReference
    ar: AfActivityReference = item.act_ref
    ebp_ir = EbpInstanceReference(
        ar.type,
        ar.instance_id,
        ar.instance_log_id,
        ar.base_template_id,
        ar.node_id,
        ar.node_iteration,
        ar.execution_manager_uris,
        ar.runtime_manager_uris,
    )

    # start the activity using REST
    ras: RemoteActivityStartingApi = cs.get_service(RemoteActivityStartingApi)
    rre: RemoteRuntimeEnvironmentApi = cs.get_service(RemoteRuntimeEnvironmentApi)
    ssc: SimpleSessionContext = ras.start_activity(body=ebp_ir)

    try:
        # Configuration values of the activity
        act_instance: ActivityInstance = ssc.act_instance
        act_conf: ActivityConfiguration = act_instance.act_conf
        # access any configuration value (values is a python dict)
        # my_other_config_value = act_conf.values['My config key']

        # input/output parameters are found in the DataContext
        dc: DataContext = ssc.data_context
        # read input from here
        pvs_in: List[ParameterValue] = dc.values
        # write output in there
        pvs_out: List[ParameterValue] = dc.output_values

        # Done? -> signal the completion via REST
        rre.application_closed(ssc.session_id, body=dc)
    except:
        rre.application_failed(999, ssc.session_id, body=ssc.data_context)
        raise


# ps = cs.process_service
# ps.start_by_id('234567-456-34-23456...')
# items = ws.get_worklist()
# print(items)

# worklist item from the worklist
item: WorklistItem = items[1]
runtime_service_example(item)
