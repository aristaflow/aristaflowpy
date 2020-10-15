
class Configuration(object):
    # TODO remote (html) runtime manager
    # TODO PIR
    def __init__(self, base_url: str, caller_uri: str):
        """
        :param baseUrl
        """
        if base_url.endswith("/"):
            base_url = base_url[0:len(base_url) - 1]
        if not(base_url.endswith("AristaFlowREST")):
            base_url = base_url + "/AristaFlowREST"
        self.__baseUrl = base_url
        self.__caller_uri = caller_uri

    @property
    def baseUrl(self) -> str:
        return self.__baseUrl

    @property
    def caller_uri(self) -> str:
        return self.__caller_uri

    def get_host(self, service_type: str, service_instance: str = None) -> str:
        """
        Returns the host definition for the given service type / instance, based on the configuration.
        :param package: The package for which to return the host, e.g. af_org_model_manager
        :return: str The host value for the requested service
        """
        if service_instance == None:
            service_instance = service_type
        return self.baseUrl + "/" + service_type + "/" + service_instance

    def get_debug(self, service_type: str, service_instance: str = None) -> bool:
        return False  # service_type == "ExecutionManager"
