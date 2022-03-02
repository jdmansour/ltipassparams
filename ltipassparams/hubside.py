
# This code runs on the hub (i.e. /opt/tljh/hub/bin/python)
# It saves the LTI parameters, so that they can be read on
# the user server side.

from typing import Dict
from tljh.user_creating_spawner import UserCreatingSpawner
from ltiauthenticator.lti11.auth import LTI11Authenticator
from jupyterhub.handlers import BaseHandler

from . import storage
from .nbgitpuller_helper import parse_nbgitpuller_link

import logging
log = logging.getLogger("LtiUserCreatingSpawner")
log.setLevel(logging.DEBUG)


class MyLTI11Authenticator(LTI11Authenticator):
    async def authenticate(self, handler: BaseHandler, data: dict = None):
        result = await super().authenticate(handler, data)
        if result:
            self.after_authenticate(result['name'], result['auth_state'])
        return result
    
    def after_authenticate(self, name: str, auth_state: dict):
        self.log.info("LTI Authentication successful! ==============")
        
        storage.store_launch_request(auth_state)

        try:
            custom_next = auth_state['custom_next']
            parsed = parse_nbgitpuller_link(custom_next)
        except KeyError:
            return


class LtiUserCreatingSpawner(UserCreatingSpawner):
    auth_state: Dict[str, str]

    async def start(self):
        try:
            keys_to_save = self.auth_state.keys()
            for key in keys_to_save:
                envname = f"LTI_{key.upper()}"
                self.environment[envname] = self.auth_state[key]

        except:
            log.exception("An exception occurred")
            pass

        result = await super().start()
        return result

    def auth_state_hook(self, spawner, auth_state):
        log.info("auth_state_hook")
        # This doesn't reach the child server
        self.auth_state = auth_state
        # should this go here, or in pre_spawn_start?
        self.environment['DEMO_FULL_NAME'] = auth_state['lis_person_name_full']
