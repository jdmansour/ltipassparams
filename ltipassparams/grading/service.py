#!/usr/bin/env python3
"""
Example grading service

This should provide an endpoint, to which an authenticated user posts a notebook to grade. The notebook will
be graded and the result passed to the LTI consumer.

In a real app, the notebook would be placed into a queue and the workflow would be a bit more complex.
"""

import json
import logging
import os
import textwrap
from urllib.parse import urlparse

import lti
from jupyterhub.services.auth import HubAuthenticated
from ltipassparams.storage import find_nbgitpuller_lti_session, get_storage
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler, authenticated

log = logging.getLogger("grading-service")

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

        storage = get_storage()
        for sess in storage:
            if sess.lti_params['user_id'] != user['name']:
                continue
            self.write(f"checkout_root: {sess.checkout_root}\n")
            self.write(f"checkout_location: {sess.checkout_location}\n")
            self.write(f"oauth_consumer_key: {sess.oauth_consumer_key}\n")
            self.write(f"lti_params:\n")
            self.write(json.dumps(sess.lti_params, indent=2) + "\n\n")

        self.write("</pre></html>")


    @authenticated
    def post(self):
        user_model = self.get_current_user()
        # notebook = "MLiP/Modul%201/MLiP_Modul_1_bias_variance.ipynb"
        notebook = self.get_argument('notebook_path')
        user_id = user_model['name']
        session = find_nbgitpuller_lti_session(notebook, user_id)

        if not session:
            self.set_header('content-type', 'text/plain')
            log.info(f"No session found for user {user_id} and path {notebook}\n")
            self.write(f"No session found for user {user_id} and path {notebook}\n")

            # debugging
            storage = get_storage()
            for sess in storage:
                self.write(f"{sess.checkout_root}, {sess.checkout_location}, {sess.lti_params['user_id']}\n")

            return
        
        # TODO: where to get this from??
        client_key = "27edf680a5fe3efbde0d07b18edab5ec57241e04dc78725b5d69ccd4e52acd95"
        secret = "db7a1eee84ae16378fa0e9f02eb805f9df412b61494b79f5a5a7fe84f8d7f84f"

        # for debugging purposes, we allow passing the grade as a parameter
        score = float(self.get_argument('debug_grade'))

        p = lti.ToolProvider(
            consumer_key=client_key,
            consumer_secret=secret,
            params=session.lti_params
        )
        res = p.post_replace_result(score)

        self.set_header('content-type', 'text/plain')

        self.write("res: %r\n" % (res,))
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


if __name__ == '__main__':
    main()
