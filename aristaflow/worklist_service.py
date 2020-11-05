from typing import List, Union

from af_worklist_manager.api.inc_client_worklists_api import IncClientWorklistsApi
from af_worklist_manager.api.inc_worklist_update_api import IncWorklistUpdateApi
from af_worklist_manager.api.worklist_update_manager_api import WorklistUpdateManagerApi
from af_worklist_manager.models.client_worklist_item import ClientWorklistItem
from af_worklist_manager.models.client_worklist_item_update import ClientWorklistItemUpdate
from af_worklist_manager.models.inc_client_worklist_data import IncClientWorklistData
from af_worklist_manager.models.inc_worklist_update_data import IncWorklistUpdateData
from af_worklist_manager.models.initial_inc_client_worklist_data import InitialIncClientWorklistData
from af_worklist_manager.models.initial_inc_worklist_update_data import InitialIncWorklistUpdateData
from af_worklist_manager.models.update_interval import UpdateInterval
from af_worklist_manager.models.worklist_revision import WorklistRevision
from af_worklist_manager.models.worklist_update_configuration import WorklistUpdateConfiguration

from .service_provider import ServiceProvider
from .worklist_model import Worklist


class WorklistService(object):
    # The fetch size for incremental worklists / updates. If None, the
    # server-side default will be used
    fetch_count: int = None
    __worklist: Worklist = None
    __items: List[ClientWorklistItem] = None
    __service_provider:ServiceProvider = None

    def __init__(self, service_provider:ServiceProvider):
        self.__items = []
        self.__service_provider = service_provider

    def create_worklist_update_configuration(self) -> WorklistUpdateConfiguration:
        """ Creates a default worklist update configuration
        """
        update_intervals: list[UpdateInterval] = []
        # worklistFilter: NO_TL or TL_ONLY
        # notify_only: if True, the initial worklist will not be returned but
        # pushed
        wuc = WorklistUpdateConfiguration(
            update_mode_threshold=3000, update_intervals=update_intervals, worklist_filter="NO_TL", notify_only=False)
        return wuc

    def get_worklist(self) -> List[ClientWorklistItem]:
        """ Updates and returns the worklist of the current user
        """
        if self.__worklist != None:
            # perform update
            return self.__items

        wum: WorklistUpdateManagerApi = self.__service_provider.get_service(
            WorklistUpdateManagerApi)
        update_conf: WorklistUpdateConfiguration = self.create_worklist_update_configuration()
        wlit: InitialIncClientWorklistData = None
        if self.fetch_count != None:
            wlit = wum.logon_and_create_client_worklist(
                body=update_conf, count=self.fetch_count)
        else:
            wlit = wum.logon_and_create_client_worklist(body=update_conf)

        self.__iterate(self.__items, wlit)

        # remember the current worklist meta data
        self.__worklist = Worklist(
            wlit.worklist_id, wlit.revision, wlit.client_worklist_id, update_conf)

        return self.__items

    def __iterate(self, items: List[ClientWorklistItem], inc: Union[InitialIncClientWorklistData, IncClientWorklistData]):
        """ Consumes an incremental client worklist until its iterator is used up
        @param items The items list to fill with the update(s)
        @param inc The first or next iteration to consume and append to items. 
        """
        if inc == None:
            return
        # append the items
        if inc.items_flat:
            items += inc.items_flat
        # iterator is used up
        if inc.dropped:
            return

        # fetch next
        inc_cl: IncClientWorklistsApi = self.__service_provider.get_service(
            IncClientWorklistsApi)
        next_it: IncClientWorklistData = inc_cl.inc_client_wl_get_next(
            inc.inc_wl_id)
        self.__iterate(items, next_it)

    def update_worklist(self) -> List[ClientWorklistItem]:
        """ Updates the user's worklist and returns the items
        """
        if self.__worklist == None:
            return self.get_worklist()

        wu: WorklistUpdateManagerApi = self.__service_provider.get_service(
            WorklistUpdateManagerApi)
        inc_updts: InitialIncWorklistUpdateData = wu.get_worklist_updates(self.__worklist.worklist_id, body=self.__worklist.revision,
                                                                          filter=self.__worklist.wu_conf.worklist_filter)

        updates: List[ClientWorklistItemUpdate] = []
        self.__iterate_updates(updates, inc_updts)
        self.__apply_worklist_updates(
            inc_updts.source_revision, inc_updts.target_revision, updates)

    def __iterate_updates(self, updates: List[ClientWorklistItemUpdate], inc: IncWorklistUpdateData):
        """ Consumes the given worklist update iterator and appends all retrieved updates to the provided updates list. 
        """
        if inc == None:
            return
        if inc.item_updates:
            updates += inc.item_updates

        if inc.dropped:
            return

        # fetch next
        iwua: IncWorklistUpdateApi = self.__service_provider.get_service(
            IncWorklistUpdateApi)
        next_it: IncWorklistUpdateData = iwua.inc_wl_updt_get_next(
            inc.inc_upd_id)
        self.__iterate_updates(updates, next_it)

    def __apply_worklist_updates(self, source_revision: WorklistRevision, target_revision: int,
                                 updates: List[ClientWorklistItemUpdate]):
        """ Applies the provided worklist updates to self.__items. Checks the consistency to the source revision,
            and performs a full update if the state does not fit. Sets the new target revision in self.__worklist.
        """
        if self.__worklist.revision.update_count != source_revision.update_count or self.__worklist.revision.initialisation_date != source_revision.initialisation_date:
            # out of order update, clear and re-fetch everything
            self.__items.clear()
            self.__worklist = None
            self.get_worklist()
            return

        for update in updates:
            self.__apply_worklist_update(update)

        # remember the update count for the next update
        self.__worklist.revision.update_count = target_revision

    def __apply_worklist_update(self, update: ClientWorklistItemUpdate):
        """ Applies the given update to __items
        """
        update_type = update.update_type
        item = update.item
        if update_type == "CHANGED":
            self.__replace_or_add_item(item)
        elif update_type == "ADDED":
            self.__items += item
        elif update_type == "REMOVED":
            self.__remove_item(item)
        elif update_type == "ADDED_OR_CHANGED":
            self.__replace_or_add_item(item)
        elif update_type == "REMOVED_OR_NOTHING":
            self.__remove_item(item)
        else:
            raise RuntimeError("Unknown update type: " + update_type)

    def __replace_or_add_item(self, item: ClientWorklistItem):
        """ Replaces or adds the given worklist item in self.__items
        """
        for i, val in self.__items:
            if item.id == val.id:
                self.__items[i] = val
                return
        # not found above, append it
        self.__items.append(val)

    def __remove_item(self, item: ClientWorklistItem):
        """ Removes the given worklist item from self.__items
        """
        for val in self.__items:
            if item.id == val.id:
                self.__items.remove(val)
                return

    def find_item_by_id(self, item_id:str) -> ClientWorklistItem:
        """ Finds a worklist item by its worklist item id. Returns none, if not in the worklist of the user.
        """
        #print(f'Finding item with id {item_id}')
        self.update_worklist()
        #print(self.__items)
        for item in self.__items:
            if item.id == item_id:
                #print('Found')
                return item
        return None