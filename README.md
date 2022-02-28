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

Then you must set a crypt key to secure the auth_state. Generate a key:

    $ openssl rand -hex 32
    883210458d42e36739c5943ca30198ecbb857eead88cde2327a19de556ffe346

and then add the following to `/etc/systemd/system/jupyterhub.service`, replacing the key with your own:

    Environment=JUPYTERHUB_CRYPT_KEY=883210458d42e36739c5943ca30198ecbb857eead88cde2327a19de556ffe346

There is a bug in jupyterhub regarding enable_auth_state.  As a workaround, apply the following patch:

```diff
--- /opt/tljh/hub/lib/python3.8/site-packages/jupyterhub/crypto.py      2022-02-28 12:45:02.542669150 +0100
+++ crypto.py.orig      2022-02-28 12:44:52.094519801 +0100
@@ -93,10 +93,7 @@
    @default('config')
    def _config_default(self):
        # load application config by default
-        try:
-            from __main__ import JupyterHub
-        except ModuleNotFoundError:
-            from .app import JupyterHub
+        from .app import JupyterHub

        if JupyterHub.initialized():
            return JupyterHub.instance().config
```

### Hub side

Right now this just uses the LtiUserCreatingSpawner as a hook. Maybe it is even sufficient to set `auth_state_hook` without a class.

### User server side

Here we use an extension.

## Todo
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