
import logging
from typing import Optional, Type

from sqlalchemy import (JSON, Column, Integer, String, UniqueConstraint,
                        create_engine)
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.orm.decl_api import DeclarativeMeta

from ltipassparams.nbgitpuller_helper import parse_nbgitpuller_link

log = logging.getLogger("JupyterHub.ltipassparams")
log.setLevel(logging.DEBUG)

DB_URL = 'sqlite:///lti_sessions.sqlite'


def get_session_factory(db_url: str = DB_URL) -> Type[Session]:
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, future=True)


Base: DeclarativeMeta = declarative_base()


class LtiSession(Base):
    __tablename__ = 'lti_sessions'
    id = Column(Integer, primary_key=True)
    lti_params = Column(JSON, nullable=False)
    oauth_consumer_key = Column(String, nullable=False)
    checkout_location = Column(String, nullable=True)
    resource_link_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    __table_args__ = (
        UniqueConstraint('resource_link_id', 'user_id'),
    )

    @property
    def checkout_root(self) -> Optional[str]:
        if self.checkout_location is None:
            return None
        return self.checkout_location.split("/")[0]


def get_session_count(db: Session):
    return db.query(LtiSession).count()


def store_launch_request(db: Session, auth_state: dict, oauth_consumer_key: str):
    log.info("Storing launch request: %r", auth_state)

    data = auth_state.copy()

    new_session = LtiSession(
        lti_params=data,
        oauth_consumer_key=oauth_consumer_key,
        resource_link_id=data['resource_link_id'],
        user_id=data['user_id'])
    try:
        log.info("Getting custom_next")
        custom_next = auth_state['custom_next']
        log.info("custom_next: %r", custom_next)
        parsed = parse_nbgitpuller_link(custom_next)
        log.info("Parsed: %r", parsed)
        if parsed:

            urlpath = parsed['urlpath']
            if urlpath.startswith("tree/"):
                urlpath = urlpath[5:]
            log.info("checkout location: %r", urlpath)
            new_session.checkout_location = urlpath

    except KeyError:
        log.exception("An exception occurred")

    # check if this pair of resource_link_id / user_id exists
    existing = (db.query(LtiSession)
                .filter(LtiSession.resource_link_id == new_session.resource_link_id,
                        LtiSession.user_id == new_session.user_id)
                .first())

    if existing:
        log.info("Found existing session")
        existing.lti_params = new_session.lti_params
        existing.checkout_location = new_session.checkout_location
        existing.oauth_consumer_key = new_session.oauth_consumer_key
        db.commit()
    else:
        log.info("Storing new session")
        db.add(new_session)
        db.commit()

    log.info("checkout_location: %r", new_session.checkout_location)
    num_sessions = db.query(LtiSession).count()
    log.info("%d items in storage", num_sessions)


def find_nbgitpuller_lti_session(db: Session, path: str, user_id: str) -> Optional[LtiSession]:
    """ Finds the LTI session belonging to a file that was
        checked out by nbgitpuller. """

    # Should we distinguish multiple LMS, by including oauth_consumer_key?
    # Theoretically, there could be multiple LMS that use the same checkout
    # location. But there would be no way to choose which one to report back to.

    session = db.query(LtiSession).where(
        LtiSession.checkout_location == path,
        LtiSession.user_id == user_id
    ).first()

    if session is not None:
        return session

    # Try to find a checkout that this file is part of
    find_root = path.split('/')[0]
    candidates = db.query(LtiSession).where(LtiSession.user_id == user_id)
    for sess in candidates:
        if sess.checkout_root == find_root:
            return sess

    return None
