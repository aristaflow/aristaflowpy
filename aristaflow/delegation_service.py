# -*- coding: utf-8 -*-
from aristaflow.abstract_service import AbstractService
from af_worklist_manager.models.worklist_item import WorklistItem
from af_worklist_manager.api.delegation_manager_api import DelegationManagerApi
from af_worklist_manager.api.del_rec_remote_iterator_api import DelRecRemoteIteratorApi
from af_worklist_manager.models.qa_initial_remote_iterator_data import QaInitialRemoteIteratorData
from typing import List, Union
from af_worklist_manager.models.qualified_agent import QualifiedAgent
from af_worklist_manager.models.qa_remote_iterator_data import QaRemoteIteratorData
from af_worklist_manager.models.delg_rec_with_comment import DelgRecWithComment
class DelegationService(AbstractService):
    '''
    Helper methods for implementing delegation
    '''

    def get_delegation_recipients(self, item:WorklistItem) -> List[QualifiedAgent]:
        """ Retrieves the possible delegation recipients for the given worklist item
        """
        dm:DelegationManagerApi = self._service_provider.get_service(DelegationManagerApi)
        drec:QaInitialRemoteIteratorData = dm.get_delegation_recipients(item.id)
        recipients:List[QualifiedAgent] = []
        self._iterate_delegation_recipients(recipients, drec)
        return recipients
    
    
    def _iterate_delegation_recipients(self, recipients:List[QualifiedAgent], cur_iter:Union[QaInitialRemoteIteratorData, QaRemoteIteratorData]):
        """ Reads up the given delegation recipients iterator
        """
        if cur_iter == None:
            return 
        if cur_iter.agents:
            recipients += cur_iter.agents
        if cur_iter.dropped:
            return
        
        api:DelRecRemoteIteratorApi = self._service_provider.get_service(DelRecRemoteIteratorApi)
        next_iter = api.del_rec_get_next(cur_iter.iterator_id)
        self._iterate_delegation_recipients(recipients, next_iter)

    def delegate(self, item:WorklistItem, comment:str, *args):
        """ Delegates the given worklist item using the given comments to all QualifiedAgents supplied in *args
            :param List[QualifiedAgents] args: Delegation recipients
        """
        dm:DelegationManagerApi = self._service_provider.get_service(DelegationManagerApi)
        body:DelgRecWithComment = DelgRecWithComment(recipients=args, comment=comment)
        dm.delegate_work_item(body, item.id)
        
        
        