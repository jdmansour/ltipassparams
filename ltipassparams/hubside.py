
# This code runs on the hub (i.e. /opt/tljh/hub/bin/python)
# It saves the LTI parameters, so that they can be read on
# the user server side.

from typing import Dict
from tljh.user_creating_spawner import UserCreatingSpawner

import logging
log = logging.getLogger("LtiUserCreatingSpawner")
log.setLevel(logging.DEBUG)

class LtiUserCreatingSpawner(UserCreatingSpawner):
    auth_state: Dict[str, str]

    async def start(self):
        log.info("start")
        try:
            log.info("Auth state:")
            log.info(type(self.auth_state))
            keys_to_save = self.auth_state.keys()
            for key in keys_to_save:
                log.info("%s: %r", key, self.auth_state[key])
                envname = f"LTI_{key.upper()}"
                self.environment[envname] = self.auth_state[key]

        except:
            log.exception("An exception occurred")
            pass

        result = await super().start()
        return result

    def auth_state_hook(self, spawner, auth_state):
        log.info("auth_state_hook")
        log.info("auth_state: %r", auth_state)
        log.info("self.unit_name: %r", self.unit_name)
        # This doesn't reach the child server
        self.auth_state = auth_state
        # should this go here, or in pre_spawn_start?
        self.environment['DEMO_FULL_NAME'] = auth_state['lis_person_name_full']
