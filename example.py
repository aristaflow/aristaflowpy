# Default Python Libraries
import json
import os
import signal
import traceback
from typing import List

# AristaFlow REST Libraries
from af_execution_manager.api.instance_control_api import InstanceControlApi
from af_execution_manager.models.templ_ref_initial_remote_iterator_data import (
    TemplRefInitialRemoteIteratorData,
)
from af_licence_manager.api.arista_flow_service_api import AristaFlowServiceApi
from af_licence_manager.api.licence_manager_api import LicenceManagerApi
from af_runtime_service import ExecutionMessage
from af_runtime_service.api.remote_activity_starting_api import RemoteActivityStartingApi
from af_runtime_service.api.remote_runtime_environment_api import RemoteRuntimeEnvironmentApi
from af_runtime_service.models.activity_configuration import ActivityConfiguration
from af_runtime_service.models.activity_instance import ActivityInstance
from af_runtime_service.models.data_context import DataContext
from af_runtime_service.models.ebp_instance_reference import EbpInstanceReference
from af_runtime_service.models.parameter_value import ParameterValue
from af_runtime_service.models.simple_session_context import SimpleSessionContext
from af_worklist_manager import ClientWorklistItemUpdate, WorklistUpdate
from af_worklist_manager.models.af_activity_reference import AfActivityReference
from af_worklist_manager.models.worklist_item import WorklistItem
from aristaflow.activity_service import SignalHandler
from aristaflow.client_platform import AristaFlowClientPlatform
from aristaflow.configuration import Configuration


conf = Configuration(
    base_url="http://localhost:81/AristaFlowREST/",
    pimage_renderer_url="http://localhost:82/AristaFlowREST/RuntimeManager/RemoteHTMLRuntimeManager/",
    rem_runtime_url="http://localhost:83/AristaFlowREST/ProcessImageRenderer/ProcessImageRenderer/",
    caller_uri="http://localhost/python",
    application_name=None
)
conf = Configuration(
    base_url="https://127.0.0.1:5000/",
    caller_uri="http://localhost/python",
    application_name=None,
    verify_ssl=False,
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


# print_connection_info()


def print_template_info():
    ic = cs.get_service(InstanceControlApi)
    tpl: TemplRefInitialRemoteIteratorData = ic.get_instantiable_templ_refs()
    print(f"Found instantiable templates: {len(tpl.templ_refs)}")


# print_template_info()

ws = cs.worklist_service
items = ws.get_worklist()

# print(f"Found {len(items)} worklist items")

ws.update_worklist_item(items[0])

def worklist_sse_push():
    def worklist_updated(updates: List[ClientWorklistItemUpdate]):
        print(f"Worklist updated, {len(items)} worklist items")

    ws.add_update_listener(worklist_updated)
    ws.enable_push_updates()
    input("Waiting and showing for worklist updates via SSE. Press return key to continue.")

def worklist_manual_update():
    ws.update_worklist()
    print(f"Found {len(items)} worklist items")

print(items[0].priority)
print(items[0].ind_priority)

# worklist_sse_push()


def runtime_service_example():
    print("Please select a worklist item")
    for i, item in enumerate(items):
        print(
            f"[{i+1}] {item.title} / {item.process_instance_name} / {item.process_template_name} ({item.state})"
        )
    sel = 0
    while sel <= 0 or sel > len(items):
        sel = int(input("Enter a number: "))
    item = items[sel - 1]

    act_service = cs.actvity_service

    class CustomSignalHandler(SignalHandler):
        def signal(self, msg: ExecutionMessage) -> bool:  # noqa: F811
            print(f"Received activity execution message: {msg}")
            # interrupt input prompt
            # os.kill(os.getpid(), signal.SIGINT)

    ac = act_service.start_sse(item, CustomSignalHandler())
    try:
        # Configuration values of the activity
        act_instance: ActivityInstance = ac.ssc.act_instance
        act_conf: ActivityConfiguration = act_instance.act_conf
        print(f"Activity config: {act_conf.values}")
        # access any configuration value (values is a python dict)
        # my_other_config_value = act_conf.values['My config key']

        # input/output parameters are found in the DataContext, ie. ac.ssc.data_context
        # if you're just interested in the values, use ac.get_input()3
        # input_data = ac.get_input()
        pvs_in: List[ParameterValue] = ac.ssc.data_context.values
        if not pvs_in:
            print("No input parameters.")
        else:
            for pv in pvs_in:
                print(f"{pv.name}: {pv.value or ''}")

        # write output
        pvs_out: List[ParameterValue] = ac.ssc.data_context.output_values
        if not pvs_out:
            print("No output parameters")
        else:
            print("Please provide values for the output parameters")
            for pv in pvs_out:
                pv.value = input(f"{pv.name} [{pv.value or ''}]: ") or pv.value

        action = ""
        while action not in ["save", "reset", "done"]:
            action = input("Enter done/reset/save: ")

        # done? -> signal via REST
        if action == "save":
            act_service.activity_suspended(ac)
        elif action == "reset":
            act_service.activity_reset(ac)
        else:
            act_service.activity_closed(ac)
    except KeyboardInterrupt:
        act_service.activity_reset(ac)
    except Exception:
        traceback.print_exc()
        # try resetting the activity
        act_service.activity_reset(ac)


# ps = cs.process_service
# ps.start_by_id('234567-456-34-23456...')
# items = ws.get_worklist()
# print(items)

# execute worklist items
while True:
    runtime_service_example()
    input("Hit enter to continue, Ctrl-C exit")
