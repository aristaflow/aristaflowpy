
class Configuration(object):
    # TODO remote (html) runtime manager
    # TODO PIR
    def __init__(self, base_url: str, caller_uri: str, verify_ssl=True, pre_shared_key:str = None, application_name:str=None, async_thread_pool_size:int = None,     
    autostart_timeout_seconds = 30):
        """
        :param baseUrl
        """
        if base_url.endswith("/"):
            base_url = base_url[0:len(base_url) - 1]
        if not(base_url.endswith("AristaFlowREST")):
            base_url = base_url + "/AristaFlowREST"
        self.__baseUrl = base_url
        self.__caller_uri = caller_uri
        self.__verify_ssl = verify_ssl
        self.__pre_shared_key = pre_shared_key
        self.__application_name = application_name
        self.__async_thread_pool_size = async_thread_pool_size
        self.__autostart_timeout_seconds = autostart_timeout_seconds

    @property
    def baseUrl(self) -> str:
        return self.__baseUrl

    @property
    def caller_uri(self) -> str:
        return self.__caller_uri

    @property
    def verify_ssl(self) -> bool:
        return self.__verify_ssl

    @property
    def pre_shared_key(self) -> str:
        return self.__pre_shared_key

    @property
    def application_name(self) -> str:
        return self.__application_name

    @property
    def async_thread_pool_size(self) -> int:
        return self.__async_thread_pool_size

    @property
    def autostart_timeout_seconds(self) -> int:
        return self.__autostart_timeout_seconds

    def get_host(self, service_type: str, service_instance: str = None) -> str:
        """
        Returns the host definition for the given service type / instance, based on the configuration.
        :param package: The package for which to return the host, e.g. af_org_model_manager
        :return: str The host value for the requested service
        """
        if service_instance == None:
            if service_type == 'RuntimeManager':
                service_instance = 'RemoteHTMLRuntimeManager'
            else:
                service_instance = service_type
        return self.baseUrl + "/" + service_type + "/" + service_instance

    def get_debug(self, service_type: str, service_instance: str = None) -> bool:
        return False
        #return service_type == "RuntimeManager"
