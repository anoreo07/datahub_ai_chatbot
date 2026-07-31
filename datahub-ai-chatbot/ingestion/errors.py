class DataHubError(Exception):
    pass


class DataHubConnectionError(DataHubError):
    pass


class DataHubAuthError(DataHubError):
    pass


class DataHubGraphQLError(DataHubError):
    pass


class DataHubTimeoutError(DataHubError):
    pass


class DataHubNotFoundError(DataHubError):
    pass


class DataHubResponseError(DataHubError):
    pass


class DataHubMappingError(DataHubError):
    pass
