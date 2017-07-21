#!/usr/bin/python
# coding: utf-8

"""
A jabber bot to order a baguette
"""

import os
import argparse
import re
import logging
import xmpp
import smtplib
import schedule
from email.mime.text import MIMEText
from jabberbot import JabberBot, botcmd

# Replace NS_DELAY variable by good one
xmpp.NS_DELAY = 'urn:xmpp:delay'


class BaguetteJabberBot(JabberBot):

    def __init__(self, *args, **kwargs):
        ''' Initialize variables. '''
        self.orders = []
        self.room = None
        self.fromm = None
        self.to = None
        self.subject = None
        self.nick = None
        self.highlight = None

        try:
            del kwargs['room']
            del kwargs['fromm']
            del kwargs['to']
            del kwargs['subject']
            del kwargs['nick']
            del kwargs['highlight']
        except KeyError:
            pass

        # answer only direct messages or not?
        self.only_direct = kwargs.get('only_direct', True)
        try:
            del kwargs['only_direct']
        except KeyError:
            pass

        # initialize jabberbot
        super(BaguetteJabberBot, self).__init__(*args, **kwargs)

        # create console handler
        chandler = logging.StreamHandler()
        # create formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # add formatter to handler
        chandler.setFormatter(formatter)
        # add handler to logger
        self.log.addHandler(chandler)
        # set level to INFO
        self.log.setLevel(logging.INFO)

        # Add some schedules
        schedule.every().monday.at("09:00").do(self.askBaguette)
        schedule.every().monday.at("09:30").do(self.sendmail)
        schedule.every().thursday.at("09:00").do(self.askBaguette)
        schedule.every().thursday.at("09:30").do(self.sendmail)
        # Debug schedules
        schedule.every(10).seconds.do(self.askBaguette)
        schedule.every(20).seconds.do(self.sendmail)

    def callback_message(self, conn, mess):
        ''' Changes the behaviour of the JabberBot in order to allow
        it to answer direct messages. This is used often when it is
        connected in MUCs (multiple users chatroom). '''

        message = mess.getBody()
        if not message:
            return

        if self.direct_message_re.match(message):
            mess.setBody(' '.join(message.split(' ', 1)[1:]))
            return super(BaguetteJabberBot, self).callback_message(conn, mess)
        elif not self.only_direct:
            return super(BaguetteJabberBot, self).callback_message(conn, mess)

    def idle_proc(self):
        """This function will be called in the main loop."""
        schedule.run_pending()
        self._idle_ping()

    def sendmail(self):
        ''' Send email '''

        if self.orders:
            msg = MIMEText("Bonjour Marie,\nEst-il possible de rapporter {} baguettes aujourd'hui ?\n\nDemandeurs :\n{}".format(
                len(self.orders),
                '\n'.join(self.orders),
                ))
            msg['Subject'] = self.subject
            msg['From'] = self.fromm
            msg['To'] = self.to

            s = smtplib.SMTP('localhost')
            s.sendmail(self.fromm, [self.to], msg.as_string())
            s.quit()

            self.send(text="J'ai envoye la commande a Marie ! cc {}".format(
                " ".join(self.orders)),
                user=self.room,
                message_type="groupchat")

            self.orders = []
        else:
            self.send(text="Pas de commande aujourd'hui !",
                      user=self.room,
                      message_type="groupchat")

    def askBaguette(self):
        ''' Demande au gens si ils veulent une baguette '''
        self.send(text="Coucou tout le monde! Voulez vous une baguette {} ?".format(self.highlight), user=self.room, message_type="groupchat")

    @botcmd
    def oui(self, mess, args):
        ''' Order a baguette '''
        user = mess.getFrom().getResource()
        if user not in self.orders:
            self.orders.append(user)

        self.send_simple_reply(mess, "OK!")

    @botcmd
    def non(self, mess, args):
        ''' Do not order a baguette '''
        user = mess.getFrom().getResource()
        if user in self.orders:
            self.orders.remove(user)

        self.send_simple_reply(mess, "OK!")

    @botcmd
    def list(self, mess, args):
        ''' List guys that ordered a baguette '''

        self.send_simple_reply(mess, 'List of guys that ordered a baguette: {}'.format(' '.join(self.orders)))


def read_password(username):
    """Read password from $HOME/.p"""
    f = open(os.environ['HOME'] + "/.p", "r+")
    for line in f.readlines():
        tuple = line.split(":")
        if tuple[0] == username:
            password = tuple[1].rstrip()
    f.close()
    return password


def parse_args():
    """
    Parse command line args
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--username",
                        help="Username")
    parser.add_argument("--room",
                        help="Room to join. Default is pcr@conference.jabber.ovh.net",
                        default="pcr@conference.jabber.ovh.net")
    parser.add_argument("--nick",
                        help="Nick name to show. Default is Boulanger",
                        default="Boulanger")
    parser.add_argument("--highlight",
                        help="Nickname to highlight when asking questions. Space separated. Default is arnaud.morin",
                        default="arnaud.morin")
    parser.add_argument("--fromm",
                        help="Mail address to send from")
    parser.add_argument("--to",
                        help="Mail address to send to")
    parser.add_argument("--subject",
                        help="Subject of mail. Default is Commande de baguette",
                        default="Commande de baguette")
    return parser.parse_args()


if __name__ == '__main__':
    "Connect to the server and run the bot forever"
    args = parse_args()
    password = read_password(args.username.replace("@jabber.ovh.net", ""))
    bot = BaguetteJabberBot(args.username, password)
    bot.room = args.room
    bot.fromm = args.fromm
    bot.to = args.to
    bot.subject = args.subject
    bot.nick = args.nick
    bot.highlight = args.highlight
    # create a regex to check if a message is a direct message
    bot.direct_message_re = re.compile('^%s?[^\w]?' % args.nick)
    bot.muc_join_room(args.room, args.nick)
    bot.serve_forever()
