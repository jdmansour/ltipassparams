#!/usr/bin/env python3
"""
Example grading service

This should provide an endpoint, to which an authenticated user posts a notebook to grade. The notebook will
be graded and the result passed to the LTI consumer.

In a real app, the notebook would be placed into a queue and the workflow would be a bit more complex.
"""

import html
import json
import logging
import os
import textwrap
from pprint import pformat
from typing import Optional
from urllib.parse import urlparse

import lti
import psutil
import traitlets.config
import traitlets.traitlets
from traitlets.utils.importstring import import_item
from jupyterhub.services.auth import HubAuthenticated
from jupyterhub.auth import Authenticator
from ltiauthenticator.lti11.auth import LTI11Authenticator
from ltipassparams import storage
from ltipassparams.storage import find_nbgitpuller_lti_session
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler, authenticated

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("grading-service")

Session = storage.get_session_factory()

class GradingHandler(HubAuthenticated, RequestHandler):
    @authenticated
    def get(self):
        self.write(textwrap.dedent("""\
        <!DOCTYPE html>
        <html>
        <h1>Submit grading</h1>
        <form method="post">
        <p>
            <label for="notebook">Notebook to grade:</label>
            <input type="text" name="notebook_path" value="MLiP/Modul%201/MLiP_Modul_1_bias_variance.ipynb" size="40">
        </p>
        <p>
            <label for="grade">Grade:</label>
            <input type="text" name="debug_grade" value="0.5">
        </p>
        <p><input type="submit" value="Submit"></p>
        </form>
        <h1>Debug</h1>
        <h2>Current User:</h2>
        <pre>"""))

        user = self.get_current_user()
        self.write(json.dumps(user, indent=2) + "\n")
        
        self.write(textwrap.dedent("""\
        </pre>
        <h2>LTI Sessions for this user:</h2>
        <pre>"""))

        with Session() as db:
            sessions = db.query(storage.LtiSession).filter(storage.LtiSession.user_id == user['name'])

            for sess in sessions:
                self.write(f"checkout_root: {sess.checkout_root}\n")
                self.write(f"checkout_location: {sess.checkout_location}\n")
                self.write(f"oauth_consumer_key: {sess.oauth_consumer_key}\n")
                self.write(f"lti_params:\n")
                self.write(json.dumps(sess.lti_params, indent=2) + "\n\n")

        self.write("</pre><pre>")
        self.write("Environment:\n" + pformat(dict(os.environ)) + "\n")

        self.write("</pre><pre>")
        consumers = get_consumers()
        self.write("LTI1.1 consumers:\n" + html.escape(pformat(consumers)) + "\n")
        
        self.write("</pre></html>")


    @authenticated
    def post(self):
        user_model = self.get_current_user()
        # notebook = "MLiP/Modul%201/MLiP_Modul_1_bias_variance.ipynb"
        notebook = self.get_argument('notebook_path')
        user_id = user_model['name']
        with Session() as db:
            session = find_nbgitpuller_lti_session(db, notebook, user_id)

        if not session:
            self.set_header('content-type', 'text/plain')
            log.info(f"No session found for user {user_id} and path {notebook}\n")
            self.write(f"No session found for user {user_id} and path {notebook}\n")

            # debugging
            with Session() as db:
                sessions = db.query(storage.LtiSession).all()
                for sess in sessions:
                    self.write(f"{sess.checkout_root}, {sess.checkout_location}, {sess.lti_params['user_id']}\n")

            return
        
        consumers = get_consumers()
        client_key = session.oauth_consumer_key
        secret = consumers[client_key]

        # for debugging purposes, we allow passing the grade as a parameter
        score = float(self.get_argument('debug_grade'))

        p = lti.ToolProvider(
            consumer_key=client_key,
            consumer_secret=secret,
            params=session.lti_params
        )
        res: lti.OutcomeResponse = p.post_replace_result(score)
        
        self.set_header('content-type', 'text/plain; charset=utf-8')

        self.write("res: %r\n" % (res,))
        self.write(f"{res.code_major}, {res.description}\n")
        self.write(f"Response code: {res.response_code}\n")
        self.write(str(res.post_response.content, encoding='utf-8', errors='replace') + "\n")
        self.write("res.is_success(): %r\n\n" % (res.is_success(),))
        self.write("LTI parameters:\n" + json.dumps(session.lti_params, indent=1, sort_keys=True))
        self.write(f"\n\nReported back score {score}")


def main():
    log.info("Starting grading service")
    prefix = os.environ['JUPYTERHUB_SERVICE_PREFIX']
    log.info("prefix: %s", prefix)
    app = Application(
        [
            (prefix, GradingHandler),
            # (url_path_join(prefix, 'oauth_callback'), HubOAuthCallbackHandler),
            (r'.*', GradingHandler),
        ],
        cookie_secret=os.urandom(32),
        debug=True,
    )

    http_server = HTTPServer(app)
    url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])
    http_server.listen(url.port, url.hostname)
    log.info("Running service now!!!! --------------")
    IOLoop.current().start()


def get_configfile() -> str:
    """ Finds the JupyterHub configuration file. """
    filename = get_configfile_from_cmdline()
    if filename:
        return filename

    if os.path.exists("/etc/jupyterhub/jupyterhub_config.py"):
        return "/etc/jupyterhub/jupyterhub_config.py"

    raise FileNotFoundError("Could not find JupyterHub configuration file")
    

def get_configfile_from_cmdline() -> Optional[str]:
    """ Tries to find the JupyterHub configuration file, when the service is ran
        as a subprocess of JupyterHub. """
    cmdline = psutil.Process().parent().cmdline()
    i = cmdline.index("-f")
    if i == -1 or i == len(cmdline) - 1:
        return None
    return cmdline[i+1]


def get_consumers():
    """ Gets the LTI 1.1 consumer keys and secrets from the configuration file."""
    configfile = get_configfile()

    # Load the traitlets configuration
    app2 = traitlets.config.Application()
    app2.load_config_file(configfile)

    # This can be a string or the class itself, so we might need evaluate it
    config_value = app2.config.JupyterHub.authenticator_class
    if isinstance(config_value, str):
        AuthKlass = import_item(config_value)
    else:
        AuthKlass = config_value
    assert issubclass(AuthKlass, Authenticator)

    # Instantiate the class, in order to get the list of consumers
    auth: LTI11Authenticator = AuthKlass(config=app2.config)
    return auth.consumers


if __name__ == '__main__':
    main()
