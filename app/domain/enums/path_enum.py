from enum import Enum

class UriBackendApiPathEnum(Enum):
    BASE_PATH = "/api/v1"#"/uri-backend/api/v1"
    GET_USER_BY_ID = BASE_PATH + "/users/"
    GET_ACCESS_TOKEN = BASE_PATH + "/auth/thirdParty/login"
    GET_LINKEDIN_USER_DATA = BASE_PATH + "/linkedIn/getUserData/"