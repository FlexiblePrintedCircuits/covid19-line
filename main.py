from flask import Flask, request, abort
from flask_sqlalchemy import SQLAlchemy
import os

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
import gspread
import json
import time

app = Flask(__name__)
app.debug = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
SECRET = os.environ["CHANNEL_SECRET"]

line_bot_api = LineBotApi(ACCESS_TOKEN)
handler = WebhookHandler(SECRET)

class InfectInfo(db.Model):
    __tablename__ = 'infect_info'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prefecture = db.Column(db.String(255))
    open_date = db.Column(db.Date)
    address = db.Column(db.String(255))
    age = db.Column(db.String(255))
    sex = db.Column(db.String(255))

    def __init__(self, prefecture, open_date, address, age, sex):
        self.prefecture = prefecture
        self.open_date = open_date
        self.address = address
        self.age = age
        self.sex = sex

@app.route("/update_data")
def update_data():

    sheets_data = {
        "type": "service_account",
        "project_id": "covid-19-270717",
        "private_key_id": "",
        "private_key": "",
        "client_email": "covid-19-line@covid-19-270717.iam.gserviceaccount.com",
        "client_id": "",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/covid-19-line%40covid-19-270717.iam.gserviceaccount.com"
    }

    sheets_data["private_key_id"] = os.environ["PRIVATE_KEY_ID"]
    sheets_data["private_key"] = os.environ["PRIVATE_KEY"].replace('\\n', '\n')
    sheets_data["client_id"] = os.environ["CLIENT_ID"]

    with open("key.json", "w") as f:
        json.dump(sheets_data, f, indent=2, ensure_ascii=False)
    
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    json_file = 'key.json'
    credentials = ServiceAccountCredentials.from_json_keyfile_name(json_file, scopes=scopes)
    http_auth = credentials.authorize(Http())
    doc_id = "1GSkhXWHoeXJTaCNAwGA2jVfkvWznLbWDFIzQ6kdBP0Y"
    client = gspread.authorize(credentials)
    gfile = client.open_by_key(doc_id)
    data_sheet  = gfile.worksheet('東京都')

    counter = 2
    delete_query = db.session.query(InfectInfo)
    delete_query.delete()

    while True:
        prefecture_val = ''
        open_date_val = ''
        address_val = ''
        age_val = ''
        sex_val = ''

        vals = data_sheet.row_values(counter)

        try:
            prefecture_val = vals[2]
            open_date_val = vals[4]
            address_val = vals[7]
            age_val = vals[8]
            sex_val = vals[9]
        except:
            break

        time.sleep(1)

        counter += 1

        if (prefecture_val != ''):
            reg = InfectInfo(prefecture_val, open_date_val, address_val, age_val, sex_val)
            db.session.add(reg)
            db.session.commit()
            print("OK: {}".format(counter))
        else:
            break
        


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text))

if __name__ == "__main__":
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)