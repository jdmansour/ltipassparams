import pytest
from ltipassparams import storage

SAMPLE_AUTH_STATE = {
    'context_id': '5a9ff6ef-82ef-4175-97b6-65976d2b8783',
    'context_title': 'Testkurs Jupyter',
    'custom_course': 'test-jupyter',
    'custom_next': 'https://jupyter-hub-staging/hub/user-redirect/git-pull?repo=https%3A%2F%2Fgithub.com%2FKI-Campus%2FMLiP&urlpath=tree%2FMLiP%2FModul+1%2FMLiP_Modul_1_bias_variance.ipynb&branch=main',
    'custom_state': 'active',
    'launch_presentation_return_url': 'https://learn.ki-campus.org/courses/test-jupyter/items/4Si7Hr0T9PHq5S22d0qIJt/tool_return',
    'lis_outcome_service_url': 'https://learn.ki-campus.org/courses/test-jupyter/items/4Si7Hr0T9PHq5S22d0qIJt/tool_grading',
    'lis_person_contact_email_primary': 'jason.mansour@gwdg.de',
    'lis_person_name_family': 'Mouse',
    'lis_person_name_full': 'Anony Mouse',
    'lis_person_name_given': 'Anony',
    'lis_result_sourcedid': 'dfbdb3c2-b9dd-4c84-85bc-9e0955df5397',
    'lti_message_type': 'basic-lti-launch-request',
    'lti_version': 'LTI-1p0',
    'resource_link_id': 'f3c485d7-d79f-4774-88ac-d881984a0a18',
    'roles': 'Learner',
    'user_id': 'myuser'
}



@pytest.fixture
def temp_db():
    Session = storage.get_session_factory("sqlite:///:memory:")
    yield Session()


def test_storage(temp_db):
    assert(storage.get_session_count(temp_db) == 0)

    storage.store_launch_request(temp_db, SAMPLE_AUTH_STATE, '123456')
    assert(storage.get_session_count(temp_db) == 1)


def test_retrieve(temp_db):
    storage.store_launch_request(temp_db, SAMPLE_AUTH_STATE, '123456')
    session = storage.find_nbgitpuller_lti_session(
        temp_db,
        'MLiP/Modul 1/MLiP_Modul_1_bias_variance.ipynb',
        'myuser')

    assert session
    assert session.lti_params['context_id'] == '5a9ff6ef-82ef-4175-97b6-65976d2b8783'
    assert session.checkout_location == 'MLiP/Modul 1/MLiP_Modul_1_bias_variance.ipynb'
    assert session.checkout_root == 'MLiP'


def test_retrieve_same_root(temp_db):
    storage.store_launch_request(temp_db, SAMPLE_AUTH_STATE, '123456')
    session = storage.find_nbgitpuller_lti_session(
        temp_db,
        'MLiP/Other',
        'myuser')

    assert session
    assert session.lti_params['context_id'] == '5a9ff6ef-82ef-4175-97b6-65976d2b8783'
    assert session.checkout_location == 'MLiP/Modul 1/MLiP_Modul_1_bias_variance.ipynb'
    assert session.checkout_root == 'MLiP'

def test_retrieve_fails(temp_db):
    storage.store_launch_request(temp_db, SAMPLE_AUTH_STATE, '123456')
    session = storage.find_nbgitpuller_lti_session(
        temp_db,
        'Non-Existing/Path',
        'myuser')

    assert session is None
