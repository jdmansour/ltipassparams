from urllib.parse import urlencode

from ltipassparams.nbgitpuller_helper import parse_nbgitpuller_link

SAMPLE_URL = "https://hub.example.com/hub/user-redirect/git-pull?repo=https%3A%2F%2Fgithub.com%2Fexample%2Ftest&urlpath=tree%2Ftest%2Findex.ipynb&branch=main"

def test_parse_url():
    result = parse_nbgitpuller_link(SAMPLE_URL)
    assert result['repo'] == 'https://github.com/example/test'
    assert result['urlpath'] == 'tree/test/index.ipynb'
    assert result['branch'] == 'main'


def test_double_encoded():
    """ Test the double-encoded URL we use to get around a bug in some LMSes. """
    url2 = "https://hub.example.com/lti/redirect?" + urlencode({'next': SAMPLE_URL})

    result = parse_nbgitpuller_link(url2)
    assert result['repo'] == 'https://github.com/example/test'
    assert result['urlpath'] == 'tree/test/index.ipynb'
    assert result['branch'] == 'main'
    