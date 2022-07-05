
import urllib.parse

def parse_nbgitpuller_link(next_url: str):
    """ Parses the LTI next_url parameter.  If it is an nbgitpuller link,
        it returns the details.

        >>> parse_next_url("http://example.com/lti/redirect?next=http%3A%2F%2Fexample.com%2Fhub%2Fuser-redirect%2Fgit-pull%3Frepo%3Dhttps%253A%252F%252Fgithub.com%252FKI-Campus%252FDatengeschichten%26urlpath%3Dtree%252FDatengeschichten%252F%26branch%3Dmain")
        {'repo': 'https://github.com/KI-Campus/Datengeschichten', 'urlpath': 'tree/Datengeschichten/', 'branch': 'main'}
    """
    
    # Undo extra redirection, if present
    parts = urllib.parse.urlparse(next_url)
    if parts.path == "/lti/redirect":
        query = urllib.parse.parse_qs(parts.query)
        try:
            next_url = query['next'][0]
        except KeyError:
            pass

    # Parse nbgitpuller link
    parts = urllib.parse.urlparse(next_url)
    if parts.path != "/hub/user-redirect/git-pull":
        return None

    query = urllib.parse.parse_qs(parts.query)
    try:
        repo = query['repo'][0]
        urlpath = query['urlpath'][0]
        branch = query['branch'][0]
    except KeyError:
        return None

    return {'repo': repo, 'urlpath': urlpath, 'branch': branch}