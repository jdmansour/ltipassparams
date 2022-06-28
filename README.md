This code helps move LTI parameters from jupyterhub to the user server, in order to access them there.

Currently this works via environment variables.  The mid-term goal would be to store LTI sessions in some kind of database on the hub side, and then to link these sessions to LTI invocations (like nbgitpuller links).  Then you could report back a score to the LTI consumer on completion of a task.

## Installation

As a prerequisite, you to set up the ltiauthenticator for Jupyter.

Install via pip. When installing for development (`install -e .`), you can link the configuration files, otherwise copy them.

```bash
sudo /opt/tljh/hub/bin/pip install -e .
sudo /opt/tljh/user/bin/pip install -e .
# Install user server extension
sudo ln -fs $PWD/jupyter-config/jupyter_notebook_config.d/ltipassparams.json /opt/tljh/user/etc/jupyter/jupyter_notebook_config.d/
# Install jupyterhub part
sudo ln -fs $PWD/config/jupyterhub_config.d/ltipassparams_spawner.py /opt/tljh/config/jupyterhub_config.d/
```

Add the following line to your configuration, e.g. in `/opt/tljh/config/jupyterhub_config.d/lti.py`:

    c.Authenticator.enable_auth_state = True

Change the authenticator to use our subclass:

    c.JupyterHub.authenticator_class = "ltipassparams.hubside.MyLTI11Authenticator"

Then you must set a crypt key to secure the auth_state. Generate a key:

    $ openssl rand -hex 32
    883210458d42e36739c5943ca30198ecbb857eead88cde2327a19de556ffe346

and then add the following to `/etc/systemd/system/jupyterhub.service`, replacing the key with your own:

    Environment=JUPYTERHUB_CRYPT_KEY=883210458d42e36739c5943ca30198ecbb857eead88cde2327a19de556ffe346

There is a bug in jupyterhub regarding enable_auth_state.  As a workaround, apply the following patch:

    sudo patch /opt/tljh/hub/lib/python3.8/site-packages/jupyterhub/crypto.py < patch/enable_auth_state_bugfix.patch

## Architecture

### Hub side

The hub part is implemented by subclassing the spawner. Maybe it would even be sufficient to use the `auth_state_hook` configuration option without a class?

- LMS sends the user to the JupyterHub
- User is authenticated
- When authentication is complete, the launch request is stored in a database. If nbgitpuller was used, this remembers the checkout location.
- If not running already, the user server is spawned.
- `LtiUserCreatingSpawner.auth_state_hook()` gets called by JupyterHub. We store the `auth_state`.
- `LtiUserCreatingSpawner.start()` gets called. This is supposed to start the child process (user server). We inject the auth state via environment variables.
    - ⚠️ What if the user server is already running, but we start a new LTI session? - The new launch request will still be stored in the database.
    - ⚠️ We shouldn't send all the LTI variables via environment vars, but only the ones we need. What is the security model of Jupyter? Can the user run untrusted code in the user server (not just the kernels)?

### User-server side

In the user's server, we use a serverextension. This implements a few things:

- For testing: When the user extension is loaded, we call `get_lti_params()` and write the LTI params to a text file.
- For testing: We hook the "tree" view and the "notebook" view and output some debugging info to the header. Including:
  - Current LTI user
  - Is this notebook part of a nbgitpuller checkout / LTI session
- A grading endpoint at `/user/<userid>/ltipassparams/submitforgrading`.  This reports back via LTI to the LMS.  Currenty, the notebook name and score are hardcoded.

## Todo
- Don't expose all LTI variables to the user's server
- ...

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