# -*- coding: utf-8 -*-
# Default Python Libraries
import asyncio
import json
import traceback
from asyncio import sleep
from typing import Generator, List, Set, Union

# Third Party Libraries
from requests import ConnectionError

# AristaFlow REST Libraries
from af_worklist_manager.api.inc_client_worklists_api import IncClientWorklistsApi
from af_worklist_manager.api.inc_worklist_update_api import IncWorklistUpdateApi
from af_worklist_manager.api.worklist_update_manager_api import WorklistUpdateManagerApi
from af_worklist_manager.models.client_worklist_item import ClientWorklistItem
from af_worklist_manager.models.client_worklist_item_update import ClientWorklistItemUpdate
from af_worklist_manager.models.client_worklist_rest_callback_data import (
    ClientWorklistRestCallbackData,
)
from af_worklist_manager.models.client_worklist_sse_callback_data import (
    ClientWorklistSseCallbackData,
)
from af_worklist_manager.models.inc_client_worklist_data import IncClientWorklistData
from af_worklist_manager.models.inc_worklist_update_data import IncWorklistUpdateData
from af_worklist_manager.models.initial_inc_client_worklist_data import InitialIncClientWorklistData
from af_worklist_manager.models.initial_inc_worklist_update_data import InitialIncWorklistUpdateData
from af_worklist_manager.models.update_interval import UpdateInterval
from af_worklist_manager.models.worklist_revision import WorklistRevision
from af_worklist_manager.models.worklist_update import WorklistUpdate
from af_worklist_manager.models.worklist_update_configuration import WorklistUpdateConfiguration

from .configuration import Configuration
from .service_provider import ServiceProvider
from .worklist_model import Worklist


# signature for worklist updates
def __update_listener(updates: List[ClientWorklistItemUpdate]):
    pass


WorklistUpdateListener = type(__update_listener)
"""
    Type for callback function for retrieving worklist updates
"""


class WorklistService(object):
    # The fetch size for incremental worklists / updates. If None, the
    # server-side default will be used
    fetch_count: int = None
    __worklist: Worklist = None
    __items: List[ClientWorklistItem] = None
    __service_provider: ServiceProvider = None
    __worklist_callback: str = None
    __worklist_update_listeners: Set[WorklistUpdateListener] = None
    __af_conf: Configuration = None
    __push_sse_client = None

    def __init__(self, service_provider: ServiceProvider, configuration: Configuration):
        self.__items = []
        self.__service_provider = service_provider
        self.__worklist_update_listeners = set()
        self.__af_conf = configuration

    def create_worklist_update_configuration(self, push: bool) -> WorklistUpdateConfiguration:
        """Creates a default worklist update configuration
        :param bool push: If set to true, create a worklist update configuration for push notifications.
        """
        update_intervals: list[UpdateInterval] = []
        if push:
            update_intervals.append(UpdateInterval(0, 200))

        # worklistFilter: NO_TL or TL_ONLY
        # notify_only: if True, the initial worklist will not be returned but
        # pushed
        wuc = WorklistUpdateConfiguration(
            update_mode_threshold=0,
            update_intervals=update_intervals,
            worklist_filter="NO_TL",
            notify_only=False,
        )
        return wuc

    def get_worklist(self, worklist_callback: str = None) -> List[ClientWorklistItem]:
        """
        Updates and returns the worklist of the current user
        :param str worklist_callback: Optionally an URL implementing the callback endpoint for push updates
        """
        if self.__worklist is not None:
            # simply return the items if push notifications are enabled
            if self.__worklist_callback is not None:
                return self.__items
            # perform update
            return self.update_worklist()

        wum: WorklistUpdateManagerApi = self.__service_provider.get_service(
            WorklistUpdateManagerApi
        )
        update_conf: WorklistUpdateConfiguration = self.create_worklist_update_configuration(True)
        wlit: InitialIncClientWorklistData = None
        if self.fetch_count is not None:
            wlit = wum.logon_and_create_client_worklist(body=update_conf, count=self.fetch_count)
        else:
            wlit = wum.logon_and_create_client_worklist(body=update_conf)

        # currently no items in the worklist
        if wlit is None:
            return self.__items

        self.__iterate(self.__items, wlit)

        # remember the current worklist meta data
        self.__worklist = Worklist(
            wlit.worklist_id, wlit.revision, wlit.client_worklist_id, update_conf, wlit.agent
        )

        if worklist_callback is not None:
            callbackData = ClientWorklistRestCallbackData(
                worklist_callback=worklist_callback,
                sub_class="ClientWorklistRestCallbackData",
                id=self.__worklist.worklist_id,
                client_worklist_id=self.__worklist.client_worklist_id,
                agent=self.__worklist.agent,
                revision=self.__worklist.revision,
                wu_conf=self.__worklist.wu_conf,
            )
            wum.register_client_worklist_callback(callbackData)
            self.__worklist_callback = worklist_callback

        return self.__items

    def enable_push_updates(self):
        """
        Enable automatic worklist updates using SSE push notifications.
        """
        if self.__push_sse_client is not None:
            return
        asyncio.run_coroutine_threadsafe(
            self._process_push_updates(), self.__service_provider.push_event_loop
        )

    async def _process_push_updates(self):
        """
        Coroutine retrieving SSE push notifications for the worklist, handling registration and reconnects
        """
        while True:
            # print("Establishing SSE connection...")
            try:
                sse_connection_id, sse_client = self.__service_provider.connect_sse(
                    WorklistUpdateManagerApi
                )
                while True:
                    # print("SSE connection established, registering for worklist push...")
                    callback_data = ClientWorklistSseCallbackData(
                        sse_conn=sse_connection_id,
                        sub_class="ClientWorklistSseCallbackData",
                        id=self.__worklist.worklist_id,
                        client_worklist_id=self.__worklist.client_worklist_id,
                        agent=self.__worklist.agent,
                        revision=self.__worklist.revision,
                        wu_conf=self.__worklist.wu_conf,
                    )
                    wum: WorklistUpdateManagerApi = self.__service_provider.get_service(
                        WorklistUpdateManagerApi
                    )
                    wum.register_client_worklist_sse(callback_data)
                    # print("Worklist registered for SSE push")
                    self.__push_sse_client = sse_client
                    for event in sse_client:
                        if event.event == "SseConnectionEstablished":
                            # print('SSE session was re-established, re-registering..')
                            callback_data.sse_conn = event.data
                            callback_data.revision = (self.__worklist.revision,)
                            wum.register_client_worklist_sse(callback_data)
                            # print("Worklist registered again for SSE push")
                        elif event.event == "client-worklist-update":
                            # print("Worklist update received")
                            try:
                                update_dict = json.loads(event.data)
                                update: WorklistUpdate = self.__service_provider.deserialize(
                                    update_dict, WorklistUpdate
                                )
                                self.__apply_worklist_updates(
                                    update.source_revision,
                                    update.target_revision,
                                    update.item_updates,
                                )
                                # call the listeners
                                self._notify_worklist_update_listeners(update.item_updates)
                            except Exception as e:
                                print("Couldn't deserialize and apply update: ", event, e)
                        else:
                            print(f"Unknown worklist SSE push event {event.event} received")
            except ConnectionError:
                # re-establish connection after some wait time
                # print("SSE disconnected...")
                await sleep(self.__af_conf.sse_connect_retry_wait)
            except Exception as e:
                print("Unknown exception caught during SSE handling", e.__class__)
                raise
            finally:
                self.__push_sse_client = None

    def add_update_listener(self, listener: WorklistUpdateListener):
        """
        Adds a listener which is called after a worklist update was received and applied.
        """
        self.__worklist_update_listeners.add(listener)

    def remove_update_listener(self, listener: WorklistUpdateListener):
        """
        Removes the given worklist update listener
        """
        self.__worklist_update_listeners.remove(listener)

    def _notify_worklist_update_listeners(self, updates: List[ClientWorklistItemUpdate]):
        """
        Notifies all registered worklist update listeners
        """
        for listener in self.__worklist_update_listeners:
            try:
                listener(updates)
            except Exception as e:
                print("Caught exception while notifying listener:", e)
                traceback.print_exc()

    def worklist_meta_data(self) -> Worklist:
        """
        Returns the worklist meta data, like ID, current revision etc., don't modify.
        """
        if self.__worklist is None:
            self.get_worklist()
        return self.__worklist

    def __iterate(
        self,
        items: List[ClientWorklistItem],
        inc: Union[InitialIncClientWorklistData, IncClientWorklistData],
    ):
        """Consumes an incremental client worklist until its iterator is used up
        @param items The items list to fill with the update(s)
        @param inc The first or next iteration to consume and append to items.
        """
        if inc is None:
            return
        # append the items
        if inc.items_flat:
            items += inc.items_flat
        else:
            return
        # iterator is used up
        if inc.dropped:
            return

        # fetch next
        inc_cl: IncClientWorklistsApi = self.__service_provider.get_service(IncClientWorklistsApi)
        next_it: IncClientWorklistData = inc_cl.inc_client_wl_get_next(inc.inc_wl_id)
        self.__iterate(items, next_it)

    def update_worklist(self) -> List[ClientWorklistItem]:
        """Updates the user's worklist and returns the items"""
        if self.__worklist is None:
            return self.get_worklist()

        if self.__push_sse_client is not None:
            return self.__items

        wu: WorklistUpdateManagerApi = self.__service_provider.get_service(WorklistUpdateManagerApi)
        inc_updts: InitialIncWorklistUpdateData = wu.get_worklist_updates(
            self.__worklist.worklist_id,
            body=self.__worklist.revision,
            filter=self.__worklist.wu_conf.worklist_filter,
        )

        if inc_updts is not None:
            updates: List[ClientWorklistItemUpdate] = []
            self.__iterate_updates(updates, inc_updts)
            self.__apply_worklist_updates(
                inc_updts.source_revision, inc_updts.target_revision, updates
            )
            self._notify_worklist_update_listeners(updates)
        return self.__items

    def __iterate_updates(
        self, updates: List[ClientWorklistItemUpdate], inc: IncWorklistUpdateData
    ):
        """Consumes the given worklist update iterator and appends all retrieved updates to the provided updates list."""
        if inc is None:
            return
        if inc.item_updates:
            updates += inc.item_updates
        else:
            return
        if inc.dropped:
            return

        # fetch next
        iwua: IncWorklistUpdateApi = self.__service_provider.get_service(IncWorklistUpdateApi)
        next_it: IncWorklistUpdateData = iwua.inc_wl_updt_get_next(inc.inc_upd_id)
        self.__iterate_updates(updates, next_it)

    def __apply_worklist_updates(
        self,
        source_revision: WorklistRevision,
        target_revision: int,
        updates: List[ClientWorklistItemUpdate],
    ):
        """Applies the provided worklist updates to self.__items. Checks the consistency to the source revision,
        and performs a full update if the state does not fit. Sets the new target revision in self.__worklist.
        """
        if (
            self.__worklist.revision.update_count != source_revision.update_count
            or self.__worklist.revision.initialisation_date != source_revision.initialisation_date
        ):
            # out of order update, clear and re-fetch everything
            self.__items.clear()
            self.__worklist = None
            self.get_worklist()
            return

        # print(f'Applying {len(updates)} updates')
        # print(updates)

        for update in updates:
            self.__apply_worklist_update(update)

        # remember the update count for the next update
        self.__worklist.revision.update_count = target_revision

    def __apply_worklist_update(self, update: ClientWorklistItemUpdate):
        """Applies the given update to __items"""
        update_type = update.update_type
        item = update.item
        if update_type == "CHANGED":
            self.__replace_or_add_item(item)
        elif update_type == "ADDED":
            self.__items += [item]
        elif update_type == "REMOVED":
            self.__remove_item(item)
        elif update_type == "ADDED_OR_CHANGED":
            self.__replace_or_add_item(item)
        elif update_type == "REMOVED_OR_NOTHING":
            self.__remove_item(item)
        else:
            raise RuntimeError("Unknown update type: " + update_type)

    def __replace_or_add_item(self, item: ClientWorklistItem):
        """Replaces or adds the given worklist item in self.__items"""
        # print('__replace_or_add_item: __items=', self.__items)
        for i in range(len(self.__items)):
            val = self.__items[i]
            if item.id == val.id:
                self.__items[i] = item
                return
        # not found above, append it
        self.__items.append(item)

    def __remove_item(self, item: ClientWorklistItem):
        """Removes the given worklist item from self.__items"""
        for val in self.__items:
            if item.id == val.id:
                self.__items.remove(val)
                return

    def find_item_by_id(self, item_id: str) -> ClientWorklistItem:
        """Finds a worklist item by its worklist item id. Returns none, if not in the worklist of the user."""
        # print(f'Finding item with id {item_id}')
        self.update_worklist()
        # print(self.__items)
        for item in self.__items:
            if item.id == item_id:
                # print('Found')
                return item
        return None
