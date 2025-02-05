import cherrypy

from ...config import conf
from .. import lib as web
from ..auth import users, Level, expose_for

from ... import db
from ...db.message import Topic, Message

from traceback import format_exc as traceback
from datetime import datetime, timedelta

@cherrypy.popargs('topicid')
@web.show_in_nav_for(0, 'inbox')
class TopicPage:
    url = 'mail'

    @staticmethod
    def can_edit(topic):
        return topic._owner == web.user() or Level.my() >= Level.supervisor

    def index_post(self, topicid, **kwargs):
        """Saves changes to a topic"""
        error = msg = ''

        # if no new topic id is given, use the one from the url
        topicid = kwargs.get('id', topicid)

        # do not save topic "new" that is nearly always wrong
        if not topicid or topicid == 'new' or kwargs.get('name') == 'new':
            error = 'No topic id given or topic id/name is "new"'
        else:
            with db.session_scope() as session:
                topic = session.get(Topic, topicid)
                if not topic:
                    topic = Topic(id=topicid, _owner=web.user(), name=topicid)
                    session.add(topic)
                    session.flush()
                elif not self.can_edit(topic):
                    error = 'Only the owner and users with elevated privileges can edit this topic.'
                    raise web.redirect(conf.url('mail', topicid, error=error))

                topic.name = kwargs.get('name', topic.name)
                topic.description = kwargs.get('description', topic.description)
                topic._owner = kwargs.get('owner', topic._owner)

                if subscribers := kwargs.get('subscribers[]'):
                    if type(subscribers) is str: subscribers = [subscribers]
                    stmt = db.sql.select(db.Person).filter(db.Person.username.in_(subscribers))
                    topic.subscribers = session.scalars(stmt).all()

        raise web.redirect(conf.url(self.url, topicid, error=error, success=msg))

    def index_get(self, topicid, error=None, success=None):
        can_edit_id = False

        with db.session_scope() as session:
            if topicid == 'new':
                owner = session.get(db.Person, web.user())
                topic = Topic(id=topicid, owner=owner, _owner=owner.username, name=topicid)
                can_edit_id = True
            else:
                topic = session.get(Topic, topicid)
                if not topic:
                    raise web.redirect(conf.url(self.url, error=f'Topic {topicid} not found'))
            me = session.get(db.Person, web.user())
            my_topics = db.sql.select(Topic).order_by(Topic.id).filter(
                db.sql.or_(
                    Topic.subscribers.contains(me),
                    Topic.owner == me
                )
            )
            return web.render(
                'topic.html',
                topic=topic,
                can_edit_id=can_edit_id,
                can_edit=True,
                persons=session.scalars(db.sql.select(db.Person).order_by(db.Person.surname).filter(db.Person.active)),
                subscribers=list(topic.subscribers),
                topics=session.scalars(my_topics),
                error=error,
                success=success,
            ).render()

    def list(self):
        ...
    @cherrypy.expose
    def index(self, topicid=None, error=None, success=None, **kwargs):

        if cherrypy.request.method == 'GET':
            if topicid:
                return self.index_get(topicid, error, success)
            else:
                return self.list()
        elif cherrypy.request.method == 'POST':
            return self.index_post(topicid, **kwargs)
        elif cherrypy.request.method == 'DELETE':
            with db.session_scope() as session:
                topic_ = session.get(Topic, topicid)
                if not topic_:
                    raise web.redirect(conf.url('job', error=f'Topic {topicid} not found'))
                if not (topic_._owner == web.user() or Level.my() >= Level.admin):
                    raise web.redirect(conf.url('job', error=f'Topic {topicid} is not yours'))
                success = f'{topicid} is deleted'
                session.delete(topicid)
            raise web.redirect(conf.url('job', success=success))


