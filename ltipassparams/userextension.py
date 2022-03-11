
# This code runs in the user's server, and recieves the LTI variables from the hubside
# module (currently via environment variables).

import logging
import os
import pwd
from pathlib import Path

from notebook.base.handlers import IPythonHandler
from notebook.notebook.handlers import NotebookHandler
from notebook.tree.handlers import TreeHandler
from notebook.notebookapp import NotebookApp

from ltipassparams.monkey import monkey_patch
from ltipassparams.storage import find_nbgitpuller_lti_session

log = logging.getLogger('NotebookApp.LtiPassParams')
log.setLevel(logging.DEBUG)

# Inject template parameters from IPythonHandler.additional_vars
# into the request

@monkey_patch(IPythonHandler, 'template_namespace')
def template_namespace(self: IPythonHandler, original_getter):
    result = original_getter()

    try:
        result.update(self.additional_vars)
    except AttributeError:
        pass

    return result

# Monkey patch `get` handler to inject additional template variables:

@monkey_patch(NotebookHandler, 'get')
def get(self: NotebookHandler, original_method, path):
    path = path.strip('/')

    self.additional_vars = {}
    # get the LTI launch associated with this path
    log.info("Looking for: %r", path)

    # get the logged in LTI user
    lti_params = get_lti_params()
    user_id = lti_params.get('user_id')
    if not user_id:
        log.warn("Could not get user_id from LTI parameters")
        return original_method(path)

    log.info("user_id is %r", user_id)
    row = find_nbgitpuller_lti_session(path, user_id)

    if not row:
        log.info("Did not find this notebook")
        return original_method(path)

    log.info("Found: %r", row)
    # found
    
    self.additional_vars['launch_presentation_return_url'] = row['launch_presentation_return_url']
    self.additional_vars['context_title'] = row['context_title']
    self.additional_vars['resource_link_id'] = row['resource_link_id']
    self.additional_vars['lis_result_sourcedid'] = row['lis_result_sourcedid']

    file_is_target = row['checkout_location'] == path
    self.additional_vars['file_is_target'] = file_is_target

    return original_method(path)


@monkey_patch(TreeHandler, 'get')
def get(self: TreeHandler, original_method, path):
    self.additional_vars = {}
    self.additional_vars['myuser'] = "TreeUser"
    return original_method(path)

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
