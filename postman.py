import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from imaplib import IMAP4_SSL
import string, random
import io, email
import sys
import os

def get_emails():
    PROJECT_ID = os.environ["PROJECT_ID"]

    # firestore setup
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
      'projectId': PROJECT_ID,
    })

    db = firestore.client()
    emails = db.collection(u'emails')

    SERVER = os.environ["IMAP_SERVER"]
    PORT = os.environ["IMAP_PORT"]
    USER = os.environ["IMAP_USER"]
    PASSWORD = os.environ["IMAP_PASSWORD"]

    # connect to server
    server = IMAP4_SSL(SERVER, port=PORT)
    print("connected to the server")

    # login
    server.login(USER, PASSWORD)
    print("authenticated")

    # set SELECT state
    server.select()
    print("set to SELECTED state")

    # list items on server
    typ, data = server.search(None, 'ALL')
    print("got list of emails")

    for num in data[0].split():
        _, data = server.fetch(num, '(RFC822)')
        message = email.message_from_bytes(data[0][1])
        email_message = {
                "from": message.get("From"),
                "date": message.get("Date"),
                "subject": message.get("Subject"),
                "id": message.get("Message-Id"),
        }

        # body
        body = ""
        if message.is_multipart():
            body = message.get_payload()[0].get_payload(decode=True)
        else:
            body = message.get_payload(decode=True)
        email_message["body"] = body.decode("utf-8")

        # category
        if email_message["subject"].lower() == "vaga":
            email_message["category"] = "job"
        else:
            email_message["category"] = "misc"

        # save in firestore
        emails.document(email_message["id"]).set(email_message)

    server.close()
    server.logout()

if __name__ == "__main__":
    get_emails()
