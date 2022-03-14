
import pickle
from dataclasses import dataclass
from typing import List, Optional

from ltipassparams.utils import find, indexof
from ltipassparams.nbgitpuller_helper import parse_nbgitpuller_link

_storage: Optional[List] = None

import logging
log = logging.getLogger("JupyterHub.ltipassparams")
log.setLevel(logging.DEBUG)

PICKLE_FILE = "/opt/tljh/state/ltipassparams.pickle"

@dataclass
class LtiSession:
    lti_params: dict
    checkout_location: Optional[str] = None

    @property
    def checkout_root(self) -> Optional[str]:
        if self.checkout_location is None:
            return None
        return self.checkout_location.split("/")[0]

def fix(row):
    if isinstance(row, dict):
        tmp = row.copy()
        checkout_location = tmp.pop('checkout_location', None)
        return LtiSession(checkout_location=checkout_location, lti_params=tmp)
    else:
        return row

def load_storage() -> List[LtiSession]:
    try:
        with open(PICKLE_FILE, "rb") as f:
            s = pickle.load(f)
            return [fix(row) for row in s]
    except FileNotFoundError:
        return []

def get_storage() -> List[LtiSession]:
    global _storage
    if _storage is None:
        _storage = load_storage()
    return _storage

def save_storage():
    global _storage
    log.debug("In save_storage")
    # log.debug("_storage: %r", _storage)
    # log.debug("get_storage(): %r", get_storage())
    with open(PICKLE_FILE, "wb") as f:
        pickle.dump(get_storage(), f)



def store_launch_request(auth_state: dict):
    storage = get_storage()

    log.info("Storing launch request: %r", auth_state)

    data = auth_state.copy()

    new_session = LtiSession(lti_params=data)
    try:
        log.info("Getting custom_next")
        custom_next = auth_state['custom_next']
        log.info("custom_next: %r", custom_next)
        parsed = parse_nbgitpuller_link(custom_next)
        log.info("Parsed: %r", parsed)
        if parsed:

            urlpath = parsed['urlpath']
            if urlpath.startswith("tree/"):
                urlpath = urlpath[5:]
            log.info("checkout location: %r" % urlpath)
            new_session.checkout_location = urlpath

        # log.info("Parsed: %r", parsed)
    except KeyError:
        log.exception("An exception occurred")
        pass

    # check if this pair of resource_link_id / user_id exists

    i = indexof(storage, lambda s: (
        s.lti_params['resource_link_id'] == data['resource_link_id'] and
        s.lti_params['user_id'] == data['user_id']
    ))

    if i is not None:
        log.info("Updating exising session for this resource_link_id / user_id pair")
        storage[i] = new_session
    else:
        storage.append(new_session)

    log.info("checkout_location: %r", new_session.checkout_location)
    log.info("%d items in storage", len(storage))
    save_storage()


def find_nbgitpuller_lti_session(path: str, user_id: str) -> Optional[LtiSession]:
    """ Finds the LTI session belonging to a file that was
        checked out by nbgitpuller. """

    # TODO: we currently get "checkout_location is not a valid LTI launch param."
    # we need to store the LTI params separately from the context.

    storage = get_storage()

    # Try to find this particular file
    session = find(storage, lambda s: (
        s.checkout_location == path and
        s.lti_params['user_id'] == user_id
    ))

    if session is not None:
        return session

    # Try to find a checkout that this file is part of
    find_root = path.split('/')[0]
    session = find(storage, lambda s: (
        s.checkout_root == find_root and
        s.lti_params['user_id'] == user_id
    ))

    return session

