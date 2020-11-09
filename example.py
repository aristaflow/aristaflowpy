from af_execution_manager.api.instance_control_api import InstanceControlApi
from af_execution_manager.models.templ_ref_initial_remote_iterator_data import TemplRefInitialRemoteIteratorData
from af_licence_manager.api.arista_flow_service_api import AristaFlowServiceApi
from af_licence_manager.api.licence_manager_api import LicenceManagerApi

from aristaflow.client_platform import AristaFlowClientPlatform
from aristaflow.configuration import Configuration
from time import sleep


conf = Configuration(base_url="http://127.0.0.1:8080/",
                     caller_uri="http://localhost/python", application_name=None)
platform = AristaFlowClientPlatform(conf)
cs = platform.get_client_service()
cs.authenticate("supervisor", "password")
# when PSK authentication is configured, no password is required
#cs.authenticate("supervisor")

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
print(f"Found {len(items)} worklist items")
ws.update_worklist()
print(f"Found {len(items)} worklist items")



#for item in items:
#    print(item.act_ref.executable_component_name)
#    if item.state != 'STARTED' and item.act_ref.executable_component_name == 'de.aristaflow.form.GeneratedForm':
#        print(item)
#        gui_context = cs.start_html_activity(item)
#        print(gui_context.url)
#        cs.reset_activity(item)
#        break

#if len(items) > 0:
#    gui_context = cs.start_html_activity(items[0])
#    print(gui_context)
