
# This code runs in the user's server, and recieves the LTI variables from the hubside
# module (currently via environment variables).

import logging
import os
import pwd
from pathlib import Path
from re import I

from notebook.notebookapp import NotebookApp

log = logging.getLogger('NotebookApp.LtiPassParams')
log.setLevel(logging.DEBUG)

# This will be replaced at some point (JupyterHub 2.0) by
# _jupyter_server_extension_paths() and
# _ load_jupyter_server_extension()
def load_jupyter_server_extension(serverapp: NotebookApp):
    log.debug("In load_jupyter_server_extension")

    # get linux user
    username = pwd.getpwuid(os.getuid())[0]
    log.debug("Logged in user: %s", username)

    lti = get_lti_params()
    log.info("LTI: %s", lti)
    if not lti:
        log.warn("No LTI params found. Is the jupyterhub part of ltipassparams running, "
                 "and is c.Authenticator.enable_auth_state = True?")

    filename = Path.home() / "userinfo.txt"
    with open(filename, "w") as f:
        for k, v in lti.items():
            log.debug("%s: %s", k, v)
            f.write("%s: %s\n" % (k, v))


def get_lti_params():
    """ Get LTI variables from environment """
    lti = {}
    for k, v in os.environ.items():
        if k.startswith('LTI_'):
            varname = k[4:].lower()
            lti[varname] = v
    return lti
