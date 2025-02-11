import cherrypy
import re
from ...config import conf
from .. import lib as web
from ..auth import users, Level, expose_for

from ... import db
from ...db.message import Topic, Message

from traceback import format_exc as traceback
from datetime import datetime, timedelta

@cherrypy.popargs('topicid')
class TopicPage:
    url = 'topic'

    @staticmethod
    def can_edit(topic):
        return topic._owner == web.user() or Level.my() >= Level.supervisor

    def index_post(self, topicid, **kwargs):
        """Saves changes to a topic"""

        error = msg = ''

        # if no new topic id is given, use the one from the url
        topicid = kwargs.get('id', topicid)

        # do not save topic "new" that is  always wrong
        if not topicid or topicid == 'new' or kwargs.get('name') == 'new':
            error = 'No topic id given or topic id/name is "new"'
        if re.search('[,\\s]', topicid):
            error = 'The topic id may not contain commas or space'
        else:
            with db.session_scope() as session:
                topic = session.get(Topic, topicid)
                if not topic:
                    topic = Topic(id=topicid, _owner=web.user(), name=topicid)
                    session.add(topic)
                    session.flush()
                elif not self.can_edit(topic):
                    error = 'Only the owner and users with elevated privileges can edit this topic.'
                    raise web.redirect(conf.url('mail', topicid), error=error)

                topic.name = kwargs.get('name', topic.name)
                topic.description = kwargs.get('description', topic.description)


        raise web.redirect(conf.url(self.url, topicid), error=error, success=msg)

    def index_get(self, topicid):
        can_edit_id = False

        with db.session_scope() as session:
            topic = session.get(Topic, topicid)
            if not topic:
                owner = session.get(db.Person, web.user())
                topic = Topic(id=topicid, owner=owner, _owner=owner.username, name='new')
                can_edit_id = True

            me = session.get(db.Person, web.user())
            my_topics = db.sql.select(Topic).order_by(Topic.id)
            messages = db.sql.select(Message).where(Message.topics.any(Topic.id == topicid)).order_by(Message.date.desc()).limit(50)
            return web.render(
                'message/topic.html',
                topic=topic,
                can_edit_id=can_edit_id,
                can_edit=self.can_edit(topic),
                persons=session.scalars(db.sql.select(db.Person).order_by(db.Person.surname).filter(db.Person.active)),
                me = me,
                subscribers=list(topic.subscribers),
                topics=session.scalars(my_topics),
                messages = session.scalars(messages).all()
            ).render()

    def list(self):
        with db.session_scope() as session:
            me = session.get(db.Person, web.user())
            topics = session.scalars(db.sql.select(Topic).order_by(Topic.id))
            return web.render('message/topic-list.html', topics=topics, me=me).render()

    @web.method.post
    @web.expose
    def toggle_sub(self, topicid, subscribe:str):
        """
        Toggles the subscription for the current user
        :param topicid: The topic
        """
        with db.session_scope() as session:
            topic = session.get(Topic, topicid)
            if not topic:
                raise web.redirect(conf.url(self.url), error=f'Topic topic:{topicid} not found')
            me = session.get(db.Person, web.user())
            if me not in topic.subscribers and subscribe == 'on':
                topic.subscribers.append(me)
                msg = 'You follow topic:' + topic.name
            elif me in topic.subscribers and subscribe == 'off':
                topic.subscribers.remove(me)
                msg = 'You unfollow topic:' + topic.name
        raise web.redirect(conf.url(self.url, topicid), success=msg)

    @cherrypy.expose
    def index(self, topicid=None, **kwargs):

        if cherrypy.request.method == 'GET':
            if topicid:
                return self.index_get(topicid)
            else:
                return self.list()
        elif cherrypy.request.method == 'POST':
            return self.index_post(topicid, **kwargs)
        elif cherrypy.request.method == 'DELETE':
            with db.session_scope() as session:
                topic_ = session.get(Topic, topicid)
                if not topic_:
                    raise web.redirect(conf.url('topic'), error=f'Topic {topicid} not found')
                if not (topic_._owner == web.user() or Level.my() >= Level.admin):
                    raise web.redirect(conf.url('topic'), error=f'Topic {topicid} is not yours')
                success = f'{topicid} is deleted'
                session.delete(topicid)
            raise web.redirect(conf.url('topic'), success=success)

@cherrypy.popargs('msgid')
@web.show_in_nav_for(0, 'envelope')
class MessagePage:

    def index_get(self, msgid, **kwargs):
        with db.session_scope() as session:
            if msgid == 'new':
                msg = Message(source='user:' + web.user())
            elif msgid:
                msg = session.get(Message, msgid)
            else:
                # Try to retrieve message dict from cherrypy session
                msg = cherrypy.session.pop('new-message', None)
                if msg:
                    msg = Message.from_dict(session, **msg)

            if type(msg) == Message:
                topics_sql = db.sql.select(Topic).order_by(Topic.id)
                sources_sql = db.sql.select(Message.source).order_by(Message.source).distinct()
                topics = session.scalars(topics_sql).all()
                sources = session.scalars(sources_sql).all()
                if msg.source not in sources:
                    sources.insert(0, msg.source)

                return web.render(
                    'message/message-edit.html',
                    title=msg.subject or 'new message',
                    topics=topics,
                    sources=sources,
                    message=msg,

                ).render()

            else:
                return self.index_list(session, **kwargs)

    def index_post(self, msgid, **kwargs):
        with db.session_scope() as session:
            msg = session.get(Message, msgid)
            if not msg:
                msg = Message(source='user:' + web.user())
                session.add(msg)


            msg.subject = kwargs.get('subject', msg.subject)
            msg.source = kwargs.get('source', msg.source)
            msg.content = kwargs.get('content', msg.content)

            if type(topics := kwargs.get('topics[]', [])) == str: topics = [topics]
            topics_sql = db.sql.select(Topic).where(Topic.id.in_(topics)).order_by(Topic.id)
            msg.topics = session.scalars(topics_sql).all()

            receivers = msg.send()

            report = f'Sent {msg.subject} to {msg.topics}, {len(receivers)} emails'
        raise web.redirect(conf.url('message'), success=report)




    def index_list(self, session, **kwargs):
        """Shows the messages as list"""

        # Get filters
        topics = web.to_list(kwargs.get('topics[]'))
        sources = web.to_list(kwargs.get('sources[]'))
        fulltext = kwargs.get('fulltext')
        page = web.conv(int, kwargs.get('page'), 1)
        limit = web.conv(int, kwargs.get('limit'), 20)
        offset = (page - 1) * limit

        # Load messages and apply filters
        messages = session.query(Message)
        if topics:
            messages = messages.filter(Message.topics.any(Topic.id.in_(topics)))
        if sources:
            messages = messages.filter(Message.source.in_(sources))
        if fulltext:
            messages = messages.where(
                db.sql.or_(
                    Message.subject.icontains(fulltext),
                    Message.content.icontains(fulltext),
                )
            )
        message_count = messages.count()
        pages = message_count // limit + 1

        messages = messages.order_by(Message.date.desc()).limit(limit).offset(offset)

        topics_sql = db.sql.select(Topic).order_by(Topic.id)
        sources_sql = db.sql.select(Message.source).order_by(Message.source).distinct()
        return web.render(
            'message/message-list.html',
            messages=messages,
            message_count=message_count,
            topics=session.scalars(topics_sql).all(),
            sources=session.scalars(sources_sql).all(),
            topics_selected=topics,
            sources_selected=sources,
            fulltext=fulltext,
            page=page,
            limit=limit,
            pages=pages

        ).render()

    @cherrypy.expose
    def index(self, msgid=None, **kwargs):
        """

        :param msgid:
        :param kwargs:
        :return:
        """
        if cherrypy.request.method == 'GET':
            return self.index_get(msgid, **kwargs)
        elif cherrypy.request.method == 'POST':
            return self.index_post(msgid, **kwargs)

    @cherrypy.expose
    def subscribers(self, **kwargs):
        """
        Returns a JSON list of users, who subscribed to topics
        :param kwargs: Needs to contain a parameter topics[]
        :return:
        """
        with db.session_scope() as session:
            topics = web.to_list(kwargs.get('topics[]'))
            topics_sql = db.sql.select(Topic).where(Topic.id.in_(topics))
            topics = session.scalars(topics_sql)
            web.mime.json.set()
            return web.as_json(db.message.subscribers(topics)).encode('utf-8')


