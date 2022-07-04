This code helps move LTI parameters from jupyterhub to the user server, in order to access them there.

Currently this works via environment variables.  The mid-term goal would be to store LTI sessions in some kind of database on the hub side, and then to link these sessions to LTI invocations (like nbgitpuller links).  Then you could report back a score to the LTI consumer on completion of a task.

## Installation

As a prerequisite, you to set up the ltiauthenticator for Jupyter.

Install via pip. When installing for development (`install -e .`), you can link the configuration files, otherwise copy them.

```bash
sudo /opt/tljh/hub/bin/pip install -e .
sudo /opt/tljh/user/bin/pip install -e .
# Install the grading service (demonstration)
sudo ln -fs $PWD/config/jupyterhub_config.d/ltipassparams_grading.py /opt/tljh/config/jupyterhub_config.d/
# Install a user server extension (this was just a test)
# sudo ln -fs $PWD/jupyter-config/jupyter_notebook_config.d/ltipassparams.json /opt/tljh/user/etc/jupyter/jupyter_notebook_config.d/
```

Add the following to your configuration, e.g. in `/opt/tljh/config/jupyterhub_config.d/lti.py`:

    c.Authenticator.enable_auth_state = True

    import ltipassparams.hubside
    c.JupyterHub.authenticator_class = ltipassparams.hubside.MyLTI11Authenticator

Then you must set a crypt key to secure the auth_state. Generate a key:

    $ openssl rand -hex 32
    883210458d42e36739c5943ca30198ecbb857eead88cde2327a19de556ffe346

and then add the following to `/etc/systemd/system/jupyterhub.service`, replacing the key with your own:

    Environment=JUPYTERHUB_CRYPT_KEY=883210458d42e36739c5943ca30198ecbb857eead88cde2327a19de556ffe346

There is a bug in jupyterhub regarding enable_auth_state.  As a workaround, apply the following patch:

    sudo patch /opt/tljh/hub/lib/python3.8/site-packages/jupyterhub/crypto.py < patch/enable_auth_state_bugfix.patch

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

### User-server side

**⚠️ Note: the following is obsolete at the moment. It doesn't really make sense to expose most of the LTI variables to the user server.**

For testing, we have a userextension that adds some debugging info to the "tree" view and the "notebook" view, including:
  - Current LTI user
  - Is this notebook part of a nbgitpuller checkout / LTI session

## Todo
- Make server load sessions again when a new one is opened 
- Use a proper database for LTI sessions, e.g. SQLite
- Make LTI sessions expire?

## Compatibility

There are two different versions of server extensions. TLJH is based on jupyterhub 1.5, which uses the "classic jupyter notebook server" based on tornado. Jupyterhub 2.0 uses the newer "Jupyter Server".

    $ /opt/tljh/hub/bin/jupyterhub --version
    Initializing JupyterHub: <jupyterhub.app.JupyterHub object at 0x7f79601af0d0>
    1.5.0

This means it currently loads the configuration from 

    /opt/tljh/user/etc/jupyter/jupyter_notebook_config.d/ltipassparams.json

and not from

    /opt/tljh/user/etc/jupyter/jupyter_server_config.d/ltipassparams.json

If Jupyterhub 2.0 is used, we will need to port this extension. See [Migrating an extension to use Jupyter Server][1]

[1]: https://jupyter-server.readthedocs.io/en/latest/developers/extensions.html#migrating-an-extension-to-use-jupyter-server