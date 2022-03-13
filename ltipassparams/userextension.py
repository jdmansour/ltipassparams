
# This code runs in the user's server, and recieves the LTI variables from the hubside
# module (currently via environment variables).

import logging
import os
import pwd
from pathlib import Path
import random

import lti

from notebook.base.handlers import IPythonHandler
from notebook.notebook.handlers import NotebookHandler
from notebook.tree.handlers import TreeHandler
from notebook.notebookapp import NotebookApp
from notebook.utils import url_path_join

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


# The following is just a demonstration.  The grading code should probably not
# run in the context of the user server, but on the hub.  The user server does
# not have access to the LTI secrets.
#
# The real flow should be something like:
#  - User authorizes submission for grading
#  - Request goes to user server
#  - User server passes this to hub
#  - Hub performs autograding (or passes the notebook on to the tutor, etc.)
#  - Hub submits result back to LTI consumer

class SubmitForGradingHandler(IPythonHandler):
    def get(self):
        self.log.info("SubmitForGradingHandler.get")
        client_key = "27edf680a5fe3efbde0d07b18edab5ec57241e04dc78725b5d69ccd4e52acd95"
        secret = "db7a1eee84ae16378fa0e9f02eb805f9df412b61494b79f5a5a7fe84f8d7f84f"

        self.log.info("lti params: %r", get_lti_params())

        # todo: get the LTI params for a certain file.
        # this just gets the last sent ones from the env vars

        notebook = "MLiP/Modul%201/MLiP_Modul_1_bias_variance.ipynb"
        user_id = get_lti_params()['user_id']
        session_params = find_nbgitpuller_lti_session(notebook, user_id).copy()
        del session_params['checkout_location']

        self.log.info("LTI session is: %r", session_params)

        p = lti.ToolProvider(
            consumer_key=client_key,
            consumer_secret=secret,
            params=session_params
        )

        self.log.info("p.is_outcome_service: %r", bool(p.is_outcome_service()))
        self.log.info("p.username: %r", p.username())

        # random number between 0 and 10
        # score = float(random.randint(0, 10)) / 10.
        score = 0.52

        self.log.info("Submitting... %f", score)
        
        # p.post_delete_result()
        res = p.post_replace_result(score, result_data={'text': 'hallo'})
        self.log.info("res: %r", res)
        self.log.info("is_success: %r", res.is_success())

        self.finish(
            "Hello from SubmitForGradingHandler\n" +
            f"File is: {notebook}\n" +
            f"Reporting back score: {score}\n"
        )

        


# This will be replaced at some point (JupyterHub 2.0) by
# _jupyter_server_extension_paths() and
# _ load_jupyter_server_extension()
def load_jupyter_server_extension(serverapp: NotebookApp):
    log.debug("In load_jupyter_server_extension")

    web_app = serverapp.web_app
    host_pattern = '.*$'
    route_pattern = url_path_join(web_app.settings['base_url'], '/ltipassparams/submitforgrading')
    web_app.add_handlers(host_pattern, [(route_pattern, SubmitForGradingHandler)])

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
