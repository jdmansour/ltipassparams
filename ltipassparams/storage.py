
from contextlib import contextmanager
from dataclasses import dataclass
from email import contentmanager
from multiprocessing import context
import pickle
from typing import Optional, List

from .nbgitpuller_helper import parse_nbgitpuller_link

_storage: Optional[List] = None

import logging
log = logging.getLogger("JupyterHub.ltipassparams")
log.setLevel(logging.DEBUG)

PICKLE_FILE = "/opt/tljh/state/ltipassparams.pickle"

@dataclass
class LtiSession:
    lti_params: dict
    checkout_location: Optional[str] = None

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
    for i in range(len(storage)):
        row = storage[i].lti_params
        if row['resource_link_id'] == data['resource_link_id'] and row['user_id'] == data['user_id']:
            # if so, update the row
            log.info("Updating exising session for this resource_link_id / user_id pair")
            storage[i] = new_session
            break
    else:
        storage.append(new_session)

    log.info("checkout_location: %r", new_session.checkout_location)
    log.info("%d items in storage", len(storage))
    save_storage()


def find_nbgitpuller_lti_session(path: str, user_id: str):
    """ Finds the LTI session belonging to a file that was
        checked out by nbgitpuller. """

    # TODO: we currently get "checkout_location is not a valid LTI launch param."
    # we need to store the LTI params separately from the context.

    s = get_storage()
    for sess in s:
        if sess.checkout_location is None:
            continue
        
        try:
            log.info("Testing: %r", sess.checkout_location)
            if sess.checkout_location == path and sess.lti_params['user_id'] == user_id:
                return sess
        except KeyError:
            log.exception("An exception occurred")
            log.info("Skipping malformed row: %r", sess)
    
    # Didn't find the particular file.  Now check if this file is part of a checkout
    checkout_dir = path.split('/')[0]
    for sess in s:
        if sess.checkout_location is None:
            continue

        try:
            row_dir = sess.checkout_location.split('/')[0]
            log.info("Testing: %r", row_dir)
            if row_dir == checkout_dir and sess.lti_params['user_id'] == user_id:
                return sess
        except KeyError:
            log.exception("An exception occurred")
            log.info("Skipping malformed row: %r", sess)

    return None