This package shows how to access LTI serssion parameters, for example in order to report scores back to a LTI Tool Consumer. It is based on and extends the [ltiauthenticator](https://github.com/jupyterhub/ltiauthenticator) packages, and understands [nbgitpuller](https://github.com/jupyterhub/nbgitpuller) links.

When the user clicks an nbgitpuller link in their learning management system (LMS), they are authenticated via LTI, and the lession is cloned from Git. This code remembers the LTI session as well as the place the files were checked out to. A sample service is provided that allows you to report a score back to the LMS. In a real-world usage, this would be integrated with a grading tool such as nbgrader or otter-grader.

## Installation

This package has been tested with The Littlest JupyterHub (TLJH).  As a prerequisite, install `ltiauthenticator` and `nbgitpuller`. Then install this via pip. The following command makes a development install, so the source files are linked and not copied.

```bash
sudo /opt/tljh/hub/bin/pip install -e .
```

Add the following to your configuration, e.g. in `/opt/tljh/config/jupyterhub_config.d/lti.py`:

    c.Authenticator.enable_auth_state = True
    c.JupyterHub.authenticator_class = 'ltipassparams.hubside.MyLTI11Authenticator'

    # Enable grading service
    import sys
    c.JupyterHub.services = [
        {
            'name': 'grading-service',
            'url': 'http://127.0.0.1:10101/',
            'command': [sys.executable, '-m', 'ltipassparams.grading_service'],
        },
    ]

    # Add the LTI 1.1 consumer key and shared secret.
    c.LTI11Authenticator.consumers = {
        # <put your key and secret here>
    }

    # Use an LTI 1.1 parameter to set the username.
    c.LTI11Authenticator.username_key = "user_id"

Then you must set a crypt key to secure the auth_state. Generate a key:

    $ openssl rand -hex 32
    883210458d42e36739c5943ca30198ecbb857eead88cde2327a19de556ffe346

and then add the following to `/etc/systemd/system/jupyterhub.service`, replacing the key with your own:

    Environment=JUPYTERHUB_CRYPT_KEY=883210458d42e36739c5943ca30198ecbb857eead88cde2327a19de556ffe346

There is a bug in jupyterhub regarding enable_auth_state.  As a workaround, apply the following patch:

    sudo patch /opt/tljh/hub/lib/python3.8/site-packages/jupyterhub/crypto.py < patch/enable_auth_state_bugfix.patch

Finally, restart your JupyterHub:

    sudo systemctl restart jupyterhub

## Architecture

### Hub side

The hub part is implemented by subclassing the authenticator.  We cannot use the `c.Spawner.auth_state_hook` option, since that only gets called when a new server is spawned - not every time the user clicks a LTI link.

- LMS sends the user to the JupyterHub
- User is authenticated
- When authentication is complete, the launch request is stored in a database. If nbgitpuller was used, it remembers the folder that the repository was cloned into.
- If not running already, the user server is spawned.

### Grading service

To implement grading, we use a [JupyterHub Service](https://jupyterhub.readthedocs.io/en/stable/reference/services.html). This does not run as the user, but is a subprocess of the hub, so it is safe. However, it has access to the user's session and ID (via cookies or OAuth).

You can access a demonstration endpoint at `/services/grading-service/`, where you can submit a score for any notebook. In reality, you would `POST` the notebook path to be graded to this URL, and it would grade it for the currently logged in user.

The service checks if the file is part of an NBGitpuller checkout, finds which LTI session that belongs to, and reports back the score.

## Todo
- Make LTI sessions expire?
- Find a better way to set JUPYTERHUB_CRYPT_KEY - is the systemd service file safe?