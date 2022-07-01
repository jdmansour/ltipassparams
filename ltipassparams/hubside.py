
# This code runs on the hub (i.e. /opt/tljh/hub/bin/python)
# It saves the LTI parameters, so that they can be read on
# the user server side.

from ltiauthenticator.lti11.auth import LTI11Authenticator
from ltiauthenticator.utils import convert_request_to_dict
from jupyterhub.handlers import BaseHandler

from . import storage


class MyLTI11Authenticator(LTI11Authenticator):
    async def authenticate(self, handler: BaseHandler, data: dict = None):
        result = await super().authenticate(handler, data)
        if result:
            # After logging in via LTI
            self.log.info("LTI Authentication successful! ==============")
            args = convert_request_to_dict(handler.request.arguments)
            oauth_consumer_key = args['oauth_consumer_key']
            storage.store_launch_request(result['auth_state'], oauth_consumer_key)
        return result
