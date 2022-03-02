
# This code runs on the hub (i.e. /opt/tljh/hub/bin/python)
# It saves the LTI parameters, so that they can be read on
# the user server side.

from typing import Dict
from tljh.user_creating_spawner import UserCreatingSpawner
from ltiauthenticator.lti11.auth import LTI11Authenticator
from jupyterhub.handlers import BaseHandler
import urllib.parse

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


def parse_nbgitpuller_link(next_url: str):
    """ Parses the LTI next_url parameter.  If it is an nbgitpuller link,
        it returns the details.

        >>> parse_next_url("http://c106-190.cloud.gwdg.de/lti/redirect?next=http%3A%2F%2Fc106-190.cloud.gwdg.de%2Fhub%2Fuser-redirect%2Fgit-pull%3Frepo%3Dhttps%253A%252F%252Fgithub.com%252FKI-Campus%252FDatengeschichten%26urlpath%3Dtree%252FDatengeschichten%252F%26branch%3Dmain")
        {'repo': 'https://github.com/KI-Campus/Datengeschichten', 'urlpath': 'tree/Datengeschichten/', 'branch': 'main'}
    """
    
    # Unpack redirection
    parts = urllib.parse.urlparse(next_url)
    if parts.path == "/lti/redirect":
        query = urllib.parse.parse_qs(parts.query)
        try:
            next_url = query['next'][0]
        except KeyError:
            pass

    parts = urllib.parse.urlparse(next_url)
    if parts.path != "/hub/user-redirect/git-pull":
        return None

    query = urllib.parse.parse_qs(parts.query)
    try:
        repo = query['repo'][0]
        urlpath = query['urlpath'][0]
        branch = query['branch'][0]
    except KeyError:
        return None

    return {'repo': repo, 'urlpath': urlpath, 'branch': branch}
