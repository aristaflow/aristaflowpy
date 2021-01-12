# AristaFlow-PY


## Examples 
The usage of all AristaFlow-PY functions requires an
`AristaFlowClientPlatform` with a valid `Configuration`. These can be
defined globally and used for all function calls.
```python
from aristaflow.client_platform import AristaFlowClientPlatform
from aristaflow.configuration import Configuration

arf_conf = Configuration(
    base_url=arf_base_url,
    caller_uri="http://localhost/python",
    application_name=None
)
arf_platform = AristaFlowClientPlatform(arf_conf)
```
<br/><br/>

### Get User Worklist
```python
def get_worklist(user, password):
    cs = arf_platform.get_client_service(user)
    if not cs.is_authenticated:
        cs.authenticate(user, password)   

    ws = cs.worklist_service
    return ws.get_worklist()
```
Returns the whole worklist of the user.
<br/> <br/>

### Get an Item of the Users Worklist by its ID
```python
def get_worklist_item(user, password, worklist_item_id):
    cs = arf_platform.get_client_service(user)
    if not cs.is_authenticated:
        cs.authenticate(user, password)   

    ws = cs.worklist_service
    return ws.find_item_by_id(worklist_item_id)
```
Returns the item from the users worklist were `id` matches `worklist_item_id`. If none is found
the function returns `None`.
<br/><br/>

### Start an Activity and Modify the Data Context
#### In 1. Function
Can be seen in `example.py`
#### In 2. Functions
##### Get DataContext
```
?
```
##### Finish Activity with Modified DataContext 
```
?
```