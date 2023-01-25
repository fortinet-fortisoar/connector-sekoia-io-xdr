from .utils import Client


def check(config) -> str:
    """
    Test API connectivity and authentication.
    Raises exceptions if something goes wrong.
    :return: "ok" indicates that the integration works like it's supposed to.
    """
    # Check a JWT token’s validity
    # https://docs.sekoia.io/develop/rest_api/identity_and_authentication/#tag/User-Authentication/operation/get_validate_resource
    headers: dict = {"Authorization": f"Bearer {config['api_key']}"}
    client: Client = Client(
        headers,
        verify=config.get("verify_certificate", False),
        proxy=config.get("proxy", False),
    )

    try:
        client.get_validate_resource()
    except Exception as e:
        if "The token is invalid" in str(e):
            return "Authorization Error: make sure API Key is correctly set"
        else:
            raise e
    return "ok"
