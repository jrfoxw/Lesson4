#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from validate import Validation
from google.appengine.ext import ndb


from logging import debug
import cgi
import os
import time
import webapp2
import jinja2


template_dir = os.path.join(os.path.dirname(__file__), 'templates')
JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                                       extensions=['jinja2.ext.autoescape'])
# set sleep time interval for local only!! #
set_time = .02

# MODELS #


class Users(ndb.Model):
    # Model for Users #
    user = ndb.StringProperty()
    password = ndb.StringProperty()
    link = ndb.StringProperty()
    tagline = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)


class ForumPost(ndb.Model):
    # Model for Forum Posts #
    poster = ndb.StringProperty()
    post = ndb.StringProperty()
    tag = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    avatar = ndb.StringProperty()


class Definitions(ndb.Model):
    # Model for word entries #
    word = ndb.StringProperty()
    definition = ndb.StringProperty()


# custom #
class SetUser(object):
        # Sets current user info #
        def __init__(self, **kwargs):
            Base.current_user = kwargs['user']
            Base.current_tag = kwargs['tagline']
            Base.current_avatar = kwargs['avatar']
            Base.login = True


# HANDLERS #
class Handler(webapp2.RequestHandler):
    # Class for Handling templates #
    def write(self, *args, **kwargs):
        self.response.out.write(*args, **kwargs)

    def render_str(self, template, ** params):
        t = JINJA_ENVIRONMENT.get_template(template)
        return t.render(params)

    def render(self, template, **kwargs):
        self.write(self.render_str(template, **kwargs))


class Register(Handler):
    # register user into database, check for possible invalid entries #
    error = False

    def get(self):
        # any errors flagged? #
        if Register.error is False:
            self.render("register.html")
        else:
            # show error flag, then reset #
            self.render("register.html", error=Register.error,
                        username=Base.current_user, avatar=Base.current_avatar,
                        tagline=Base.current_tag)
            Register.error = False

    def post(self):
        # gather registration info #
        username = cgi.escape(self.request.get('username'))
        password = cgi.escape(self.request.get('password'))
        avatar = self.request.get('avatar')
        tagline = cgi.escape(self.request.get('tagline'))

        # Run Validation #
        validate = Validation('register', username=username,
                              password=password, avatar=avatar,
                              tagline=tagline)
        validate.run_validation()
        if self.check_user(username):
            # check if username is duplicate #
            self.redirect('/register.html')
        elif validate.error_return():
            # set error flag if any #
            Register.error = validate.error_return()
            self.redirect('/register.html')
        elif not Register.error:
            # set user as active #
            SetUser(user=username, avatar=avatar, tagline=tagline)
            # add user info to database. #
            new_user = Users(user=username,
                             password=password,
                             link=avatar,
                             tagline=tagline)
            new_user.put()
            time.sleep(set_time)
            self.redirect('/forum.html')

    def check_user(self, user):
        # checks if username is already in DB #
        check = Base.query_users.fetch()
        for field in check:
            debug('User being checked --{}'.format(field.user))
            if user == field.user:
                # set error flag #
                Register.error = '*{}* is unavailable as a username.'.format(user)
                return Register.error
        return Register.error


class Definition(Handler):
    # shows definitions and allows user to enter in new entries does not have to be registered #
    error = False

    def get(self):
        word_list = Definitions.query().order(Definitions.word).fetch()
        if Definition.error:
            self.render("definitions.html", wordlist=word_list, login=Base.login,
                        user=Base.current_user, u_image=Base.current_avatar,
                        error=Definition.error)
            Definition.error = False
        else:
            self.render("definitions.html",  wordlist=word_list, login=Base.login,
                        user=Base.current_user, u_image=Base.current_avatar)

    def post(self):
        word = cgi.escape(self.request.get('word'))
        definition = cgi.escape(self.request.get('definition'))
        # validate information #
        validate = Validation('', word=word, definition=definition)
        validate.run_validation()

        if not validate.error_return():
            # looks good now add to DB #
            define = Definitions(word=word, definition=definition)
            define.put()
            # for local #
            time.sleep(set_time)
            Base.login = True
            self.redirect('/definitions.html')
        else:
            # set error flag #
            Definition.error = validate.error_return()
            self.redirect('definitions.html')


class NotesData(Handler):
    # Notes Handler #
    def get(self):
        user = Base.current_user
        self.render("notes.html", login=Base.login,
                    user=user, u_image=Base.current_avatar,)


class ForumPage(Handler):
    # Allows registered user to enter in a post, does not allow for blank posts #
    error = False

    def get(self):
        posts = ForumPost.query().order(ForumPost.date).fetch()
        total_posts = len(posts)
        if ForumPage.error is False:
            # looks good process page #
            debug('Total posts = {}'.format(total_posts))

            self.render("/forum.html",
                        post_list=posts,
                        login=Base.login,
                        user=Base.current_user,
                        u_image=Base.current_avatar,
                        total_posts=total_posts)

        else:
            # errors on page so will show error flag #
            self.render("/forum.html",
                        post_list=posts,
                        login=Base.login,
                        user=Base.current_user,
                        u_image=Base.current_avatar,
                        error=ForumPage.error,
                        total_posts=total_posts)
            # error being shown, so reset error flag #
            ForumPage.error = False

    def post(self):
        # get current registered user and post #
        post = cgi.escape(self.request.get("post"))
        poster = Base.current_user
        tag = Base.current_tag
        avatar = Base.current_avatar
        debug('....POSTING...')

        if post:
            # looks good add post to database #
            forum_post = ForumPost(post=post, poster=poster, tag=tag, avatar=avatar)
            forum_post.put()
            debug('Post added--')
            # for local #
            time.sleep(set_time)
            Base.login = True
            self.redirect('/forum.html')

        else:
            # set error flag #
            ForumPage.error = 'Can not post a blank post..'
            self.redirect('/forum.html')


class MainPage(Handler):
    # MainPage (index.html) Handler #
    error = ''

    def get(self):

        is_logged = Base.login
        if not is_logged:
            self.redirect('/login.html')
            return
        fetch_one = 1
        latest_post = ForumPost.query().order(-ForumPost.date).fetch(fetch_one)
        # test to see if registered user is or is not logged in #

        debug('LOGOUT STATUS = {}'.format(is_logged))
        if Base.current_user == '':
            Base.login = False

        if Base.login is False and MainPage.error is False:
            debug('Both are False')
            self.render("index.html", login=False, latest_post=latest_post)

        elif Base.login is False and MainPage.error:
            debug('Contains and Error')
            self.render("index.html", login=False, latest_post=latest_post, error=MainPage.error)
            MainPage.error = False

        else:
            debug('Login is True!')
            self.render("index.html",
                        login=True,
                        user=Base.current_user,
                        u_image=Base.current_avatar,
                        latest_post=latest_post)
            # MainPage.error = False

    def post(self):

        # get user name and password and check for invalid characters #
        qualify_user = cgi.escape(self.request.get("username"))
        qualify_pass = cgi.escape(self.request.get("password"))

        # if user has valid creds then set login flag and user info #
        if qualify_user and qualify_pass:
            if self.check_creds(qualify_user, qualify_pass):
                MainPage.error = False
                self.render("index.html", login=True,
                            user=Base.current_user, u_image=Base.current_avatar)


            else:
                # no creds did not validate, set error flag #
                MainPage.error = 'You\'ve entered the wrong name or password..'
                self.render("index.html", login=False, error=MainPage.error)
                MainPage.error = False

        else:
            self.render("index.html", login=Base.login)


    def check_creds(self, user, password):
        # qualify user against user info in database#
        for fields in Base.query_users:
            if str(fields.user) == str(user) and \
               str(fields.password) == str(password):
                SetUser(user=fields.user,
                        tagline=fields.tagline,
                        avatar=fields.link,
                        )
                return True


class Login(Handler):
    def get(self):
        Base.login = False
        self.render("login.html", login=Base.login)

    def post(self):
        Base.login = False
        self.render("login.html")



class Base(Handler):
    # Base Template Handler #
    query_users = Users.query()
    # Initialize base user info #
    login = False
    current_user = ''
    current_tag = ''
    current_avatar = ''
    
    def get(self):
        self.render("base.html", login=Base.login)

    def post(self):
        debug('logout')

router = [('/', MainPage),
          ('/notes.html', NotesData),
          ('/definitions.html', Definition),
          ('/register.html', Register),
          ('/forum.html', ForumPage),
          ('/base.html', Base),
          ('/login.html', Login)
          ]
app = webapp2.WSGIApplication(router, debug=True)

