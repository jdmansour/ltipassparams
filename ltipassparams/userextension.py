
# This code runs in the user's server, and recieves the LTI variables from the hubside
# module (currently via environment variables).

import logging

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
def NotebookHandler_get(self: NotebookHandler, original_method, path):
    path = path.strip('/')

    self.additional_vars = {}
    # get the LTI launch associated with this path
    log.info("Looking for: %r", path)

    # get the logged in user
    user = self.get_current_user()
    try:
        user_id = user['name']
    except TypeError:
        log.warn("Could not get the user ID")
        return original_method(path)

    self.additional_vars['user_id'] = user_id
    self.log.info("user_id is %r", user_id)

    # TODO: we should probably get this via a REST api,
    # so we don't have sensitive data in the user process
    session = find_nbgitpuller_lti_session(path, user_id)

    if not session:
        log.info("Did not find this notebook")
        return original_method(path)

    row = session.lti_params
    log.info("Found: %r", row)
    # found
    
    self.additional_vars['launch_presentation_return_url'] = row['launch_presentation_return_url']
    self.additional_vars['context_title'] = row['context_title']
    self.additional_vars['resource_link_id'] = row['resource_link_id']

    file_is_target = (session.checkout_location == path)
    self.additional_vars['file_is_target'] = file_is_target

    return original_method(path)


@monkey_patch(TreeHandler, 'get')
def TreeHandler_get(self: TreeHandler, original_method, path):
    self.additional_vars = {}
    user = self.get_current_user()
    try:
        user_id = user['name']
    except TypeError:
        user_id = "anonymous"
    self.additional_vars['user_id'] = user_id
    return original_method(path)


# This will be replaced at some point (JupyterHub 2.0) by
# _jupyter_server_extension_paths() and
# _ load_jupyter_server_extension()
def load_jupyter_server_extension(serverapp: NotebookApp):
    log.debug("In load_jupyter_server_extension")
