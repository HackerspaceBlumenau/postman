import string, random, io, email, sys, os, base64, re, json
import logging as log
from imaplib import IMAP4_SSL
from email.utils import parsedate_to_datetime
from datetime import datetime
import slack

def send_messages_to_slack(msg):
    log.basicConfig(level=log.DEBUG)

    # log message
    log.debug(msg)

    category = msg["category"]

    if not "body" in msg:
        log.info("ignoring message without body key")
        return

    body = msg["body"]

    _from = ""
    if "from" in msg:
        _from = msg["from"]

    subject = ""
    if "subject" in msg:
        subject = msg["subject"]

    # convert category map
    SLACK_CATEGORY_MAP = os.environ["SLACK_CATEGORY_MAP"]
    category_map = json.loads(base64.b64decode(SLACK_CATEGORY_MAP))
    if not category in category_map:
        log.info("ignoring not routed category {}".format(category))
        return

    channels = category_map[msg["category"]]

    slack_message = ""
    if _from != "":
        slack_message += "*De:* {}".format(_from)
    if subject != "":
        slack_message += "\n*Assunto:* {}".format(subject)
    slack_message += "\n```{}```".format(body)

    SLACK_API_TOKEN = os.environ["SLACK_API_TOKEN"]
    client = slack.WebClient(token=SLACK_API_TOKEN)
    for channel in channels:
        response = client.chat_postMessage(
            icon_emoji=":capivara:",
            channel=channel,
            text=slack_message)

        assert response["ok"]

def run(*args):
    log.basicConfig(level=log.DEBUG)

    log.debug(args)

    # setup client
    SERVER = os.environ["IMAP_SERVER"]
    PORT = os.environ["IMAP_PORT"]
    USER = os.environ["IMAP_USER"]
    PASSWORD = os.environ["IMAP_PASSWORD"]

    # connect to server
    server = IMAP4_SSL(SERVER, port=PORT)
    log.info("connected to the server")

    # login
    server.login(USER, PASSWORD)
    log.info("authenticated")

    # set SELECT state
    server.select()
    log.info("set to SELECTED state")

    # list items on server
    typ, data = server.search(None, '(UNSEEN)')
    log.info("got list of emails")

    messages_to_send = []
    split = data[0].split()
    for num in split:
        log.info("processing message {} from {}".format(num.decode("utf-8"), len(split)))
        _, data = server.fetch(num, '(RFC822)')
        message = email.message_from_bytes(data[0][1])

        date = parsedate_to_datetime(message.get("Date"))

        # body
        body = None
        if message.is_multipart():
            msg = message.get_payload()
            while type(msg) == list:
                temp = msg[0].get_payload(decode=True)
                if temp == None:
                    msg = msg[0].get_payload()
                else:
                    msg = temp
            body = msg.decode("utf-8", "ignore")

        else:
            body = message.get_payload(decode=True).decode("utf-8")

        # if successful extract body
        if body != None and body != "":
            cleanhtml = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
            body = re.sub(cleanhtml, '', body)
            email_message = {
                    "id": num,
                    "message_id": message.get("Message-Id"),
                    "from": message.get("From"),
                    "subject": message.get("Subject"),
                    "date": date,
                    "body": body,
                    "category": "misc",
            }

            # category
            if email_message["subject"].lower() == "vaga":
                email_message["category"] = "job"

            messages_to_send.append(email_message)

    if len(messages_to_send) == 0:
        log.info("no new message")
        return

    for email_message in messages_to_send:
        send_messages_to_slack(email_message)
        server.uid('STORE', num, '+FLAGS', '(\Seen)')

    server.close()
    server.logout()

if __name__ == "__main__":
    run()
