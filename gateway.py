#!/usr/bin/env python

#   Copyright 2012 Josh Kearney
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import os
import pyfire
import sleekxmpp


def env(var):
    return os.environ[var]


class CampfireXmppGateway(sleekxmpp.ClientXMPP):
    def __init__(self):
        self.xmpp_username = env("CXG_XMPP_USERNAME")
        self.xmpp_password = env("CXG_XMPP_PASSWORD")
        self.xmpp_recipient = env("CXG_XMPP_RECIPIENT")

        self.cf_subdomain = env("CXG_CAMPFIRE_SUBDOMAIN")
        self.cf_room_name = env("CXG_CAMPFIRE_ROOM")
        self.cf_real_name = env("CXG_CAMPFIRE_REAL_NAME")
        self.cf_username = env("CXG_CAMPFIRE_USERNAME")
        self.cf_password = env("CXG_CAMPFIRE_PASSWORD")

        self.cf = pyfire.Campfire(self.cf_subdomain, self.cf_username,
                                  self.cf_password, ssl=True)

        self.cf_room = None
        self.cf_stream = None

        sleekxmpp.ClientXMPP.__init__(self, self.xmpp_username,
                                      self.xmpp_password)

        self.add_event_handler("session_start", self.xmpp_session_start)
        self.add_event_handler("session_end", self.xmpp_session_end)
        self.add_event_handler("message", self.xmpp_incoming_message)

    def xmpp_session_start(self, event):
        self.send_presence()
        self.get_roster()

        self.cf_room = self.cf.get_room_by_name(self.cf_room_name)
        self.cf_room.join()

        self.cf_stream = self.cf_room.get_stream()
        self.cf_stream.attach(self.campfire_process_incoming).start()

    def xmpp_session_end(self, event):
        self.cf_stream.stop().join()

    def xmpp_incoming_message(self, message):
        if message["type"] in ("chat", "normal"):
            self.cf_room.speak(message["body"])

    def campfire_send_message(self, message):
        self.send_message(self.xmpp_recipient, message)

    def campfire_process_incoming(self, message):
        user = None
        if message.user:
            user = message.user.name

        if user == self.cf_real_name:
            return

        response = None
        if message.is_joining():
            response = "[%s entered the room]" % user
        elif message.is_leaving():
            response = "[%s left the room]" % user
        elif message.is_tweet():
            response = "[%s] %s tweeted '%s' - %s" % (user,
                                                      message.tweet["user"],
                                                      message.tweet["tweet"],
                                                      message.tweet["url"])
        elif message.is_text():
            response = "[%s] %s" % (user, message.body)
        elif message.is_upload():
            response = "[%s uploaded %s: %s]" % (user, message.upload["name"],
                                                 message.upload["url"])
        elif message.is_topic_change():
            response = "[%s changed topic to '%s']" % (user, message.body)

        if response:
            self.campfire_send_message(response)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format="%(levelname)-8s %(message)s")

    gateway = CampfireXmppGateway()
    gateway.connect()
    gateway.process(block=True)
