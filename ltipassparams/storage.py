
from contextlib import contextmanager
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

def load_storage():
    try:
        with open(PICKLE_FILE, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return []

def get_storage():
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
            data['checkout_location'] = urlpath

        # log.info("Parsed: %r", parsed)
    except KeyError:
        log.exception("An exception occurred")
        pass

    # check if this pair of resource_link_id / user_id exists
    for i in range(len(storage)):
        row = storage[i]
        if row['resource_link_id'] == data['resource_link_id'] and row['user_id'] == data['user_id']:
            # if so, update the row
            log.info("Updating exising session for this resource_link_id / user_id pair")
            storage[i] = data
            break
    else:
        storage.append(data)

    log.info("checkout_location: %r", data.get("checkout_location", "-"))
    log.info("%d items in storage", len(storage))
    save_storage()


def find_nbgitpuller_lti_session(path: str, user_id: str):
    """ Finds the LTI session belonging to a file that was
        checked out by nbgitpuller. """

    # TODO: we currently get "checkout_location is not a valid LTI launch param."
    # we need to store the LTI params separately from the context.

    s = get_storage()
    for row in s:
        if 'checkout_location' not in row:
            continue
        
        try:
            log.info("Testing: %r", row['checkout_location'])
            if row['checkout_location'] == path and row['user_id'] == user_id:
                return row
        except KeyError:
            log.exception("An exception occurred")
            log.info("Skipping malformed row: %r", row)
    
    # Didn't find the particular file.  Now check if this file is part of a checkout
    checkout_dir = path.split('/')[0]
    for row in s:
        if 'checkout_location' not in row:
            continue

        try:
            row_dir = row['checkout_location'].split('/')[0]
            log.info("Testing: %r", row_dir)
            if row_dir == checkout_dir and row['user_id'] == user_id:
                return row
        except KeyError:
            log.exception("An exception occurred")
            log.info("Skipping malformed row: %r", row)

    return None