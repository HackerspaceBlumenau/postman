import string, random, io, email, sys, os, base64, re, json
import logging as log
from imaplib import IMAP4_SSL
from email.utils import parsedate_to_datetime
from datetime import datetime
from google.cloud import pubsub_v1
import slack

def send_messages_to_slack(event, context):
    log.basicConfig(level=log.DEBUG)

    # log event and context
    log.debug(event, context)

    # translate message
    msg = json.loads(base64.b64decode(event['data']).decode('utf-8'))
    if not "category" in msg:
        log.info("ignoring message without category key")
        return

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

def get_emails(trigger):
    log.basicConfig(level=log.DEBUG)

    # log trigger
    log.debug(trigger)

    PUB_SUB_CREDENTIALS = os.environ["GOOGLE_PUB_SUB_CREDENTIALS"]
    CREDENTIALS_FILE = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

    # save credentials to temporarly file
    cred_file = open(CREDENTIALS_FILE , "w+")
    cred_content = base64.b64decode(PUB_SUB_CREDENTIALS )
    cred_file.write(cred_content.decode("utf-8"))
    cred_file.close()
    log.debug("saved credentials to {}".format(CREDENTIALS_FILE))

    PROJECT_ID = os.environ["PROJECT_ID"]
    TOPIC_NAME = os.environ["TOPIC_NAME"]

    # setup client
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_NAME)

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
    typ, data = server.search(None, 'ALL')
    log.info("got list of emails")

    split = data[0].split()
    for num in split:
        log.info("processing message {} from {}".format(num.decode("utf-8"), len(split)))
        _, data = server.fetch(num, '(RFC822)')
        message = email.message_from_bytes(data[0][1])

        date = parsedate_to_datetime(message.get("Date"))
        #if date.date() < datetime.today().date():
        #    log.info("ignoring old message")
        #    continue

        #if date.hour != datetime.now().hour:
        #    log.info("ignoring old message")
        #    continue

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
                    "id": message.get("Message-Id"),
                    "from": message.get("From"),
                    "subject": message.get("Subject"),
                    "date": date,
                    "body": body,
                    "category": "misc",
            }

            # category
            if email_message["subject"].lower() == "vaga":
                email_message["category"] = "job"

            # send to publisher
            publish_message = bytes(json.dumps(email_message, indent=4, sort_keys=True, default=str), "utf-8")
            publisher.publish(topic_path, data=publish_message)

    server.close()
    server.logout()

if __name__ == "__main__":
    get_emails(None)
    #send_messages_to_slack(b'{"from":"User <user@example.org","subject":"Subject Example","category":"misc","body":"Hello World!"}')
