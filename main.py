from flask import Flask, request, abort
from flask_sqlalchemy import SQLAlchemy

import os
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
)

from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
import gspread

import boto3

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

aws_s3_bucket = os.environ['AWS_BUCKET']

class InfectInfo(db.Model):
    __tablename__ = 'infect_info'

    id = db.Column(db.Integer, primary_key=True)
    prefecture = db.Column(db.String(255))
    open_date = db.Column(db.Date)
    address = db.Column(db.String(255))
    age = db.Column(db.String(255))
    sex = db.Column(db.String(255))

    def __init__(self, id, prefecture, open_date, address, age, sex):
        self.id = id
        self.prefecture = prefecture
        self.open_date = open_date
        self.address = address
        self.age = age
        self.sex = sex


def get_data(get_prefecture):
    all_data = db.session.query(InfectInfo).filter(InfectInfo.prefecture==get_prefecture).all()
    
    all_infecters = len(all_data)
    all_men_infecters = 0
    all_women_infecters = 0
    by_age_infecters = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    
    for data in all_data:
        if (data.sex == "男性"):
            all_men_infecters += 1
        elif (data.sex == "女性"):
            all_women_infecters += 1
        
        if (data.age == "10歳未満"):
            by_age_infecters[0] += 1
        else:
            age = int(data.age[0])
            by_age_infecters[age] += 1

    
    send_message = "{}の新型コロナウイルス感染症　感染者データ\n\n総感染者数：{}\n\n男性：{}人\n女性：{}人\n\n画像は、年代別の感染者数を表したグラフです。".format(get_prefecture, all_infecters, all_men_infecters, all_women_infecters)

    labels = ["Under 10", "10~", "20~", "30~", "40~", "50~", "60~", "70~", "80~", "90~"]
    height = by_age_infecters
    plt.bar(labels, height, color="#1E7F00")

    file_name = "by_age_{}.png".format(get_prefecture)
    plt.savefig(file_name)

    s3_resource = boto3.resource('s3')
    s3_resource.Bucket(aws_s3_bucket).upload_file(file_name, file_name)

    s3_client = boto3.client('s3')
    s3_image_url = s3_client.generate_presigned_url(
        ClientMethod = 'get_object',
        Params       = {'Bucket': aws_s3_bucket, 'Key': file_name},
        ExpiresIn    = 10,
        HttpMethod   = 'GET'
    )

    return [send_message, s3_image_url]

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

    db_id = 1

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
            reg = InfectInfo(db_id, prefecture_val, open_date_val, address_val, age_val, sex_val)
            db_id += 1
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
    if (event.message.text == "東京都"):
        send_list = get_data("東京都")

        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text=send_list[0]),
                ImageSendMessage(
                    original_content_url = send_list[1],
                    preview_image_url = send_list[1]
                )
            ]
        )

if __name__ == "__main__":
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)
