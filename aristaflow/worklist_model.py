'''
Worklist model classes
'''
from af_worklist_manager.models.worklist_revision import WorklistRevision
from af_worklist_manager.models.worklist_update_configuration import WorklistUpdateConfiguration


class Worklist(object):
    ''' Simply aggregates the few relevant properties of a worklist
    '''

    worklist_id: str = None
    revision: WorklistRevision = None
    client_worklist_id: int = None
    wu_conf: WorklistUpdateConfiguration = None

    def __init__(self, worklist_id: str, revision: WorklistRevision, client_worklist_id: int, wu_conf: WorklistUpdateConfiguration):
        '''
        Constructor
        '''
        self.worklist_id = worklist_id
        self.revision = revision
        self.client_worklist_id = client_worklist_id
        self.wu_conf = wu_conf
        pass
