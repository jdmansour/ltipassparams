# grading service
import sys

c.JupyterHub.services = [
    {
        'name': 'grading-service',
        'url': 'http://127.0.0.1:10101/',
        'command': [sys.executable, '-m', 'ltipassparams.grading.service'],
    },
]