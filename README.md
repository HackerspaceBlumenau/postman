# Postman

> Read messages from IMAP server and send to slack channels

### Getting started

Set this environment varibles:

```
# imap server address
IMAP_SERVER

# imap server port
IMAP_PORT

# imap server user
IMAP_USER=

# imap server password
IMAP_PASSWORD=

# slack category map in format base64({"category":["list","of","channels"]})
SLACK_CATEGORY_MAP=

# slack api token for the bot user
SLACK_API_TOKEN=
```

Then run the main.py file:

```
python3 ./main.py
```

Check your workspace in channels that you map using the SLACK_CATEGORY_MAP environment variable

### Available Categories

List of supported categories

"job" = When subject is equal to "vaga"

"misc" = All others categories

### Maintainers

Jonathan A. Schweder <jonathanschweder@gmail.com> @jaswdr

### License

MIT
