import os
import re
from threading import Thread

from flask import Flask, request, make_response
from dotenv import dotenv_values
import openai
import requests
from slack_sdk import WebClient

config = dotenv_values(".env")
openai.organization = config.get("GPT_ORG")
openai.api_key = config.get("GPT_KEY")

botmsg = {}
token = config.get("SLACK_REPLY_CHANNEL_TOKEN")
slack = WebClient(token=token)

app = Flask(__name__)

def e404():
    return ("-_-///", 404)

def gpt(text):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=[{
                "role": "user",
                "content": text
            }]
        )
        chs = res.get("choices", [])
        if len(chs) == 0: return '[no reply]'
        return chs[0].get("message").get("content")
    except:
        return '[sorry, internal error]'

def context_gpt(history):
    try:
        messages = []
        for h in history:
            if not h[1]: continue
            if h[0]:
                messages.append({ "role": "assistant", "content": h[1] })
            else:
                messages.append({ "role": "user", "content": h[1] })
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages
        )
        chs = res.get("choices", [])
        if len(chs) == 0: return '[no reply]'
        return chs[0].get("message").get("content")
    except:
        return '[sorry, internal error]'

def async_gpt(msgid, user, text, ts, channel):
    if msgid in botmsg: return
    botmsg[msgid] = True
    try:
        reply = gpt(text)
        if not reply: reply = '[empty]'
        #print("[gpt]", user, reply)
        slack.chat_postMessage(channel=channel, text=reply, thread_ts=ts)
    except:
        pass
    botmsg.pop(msgid)

def async_context_gpt(msgid, user, text, thread_ts, channel):
    if msgid in botmsg: return
    botmsg[msgid] = True
    try:
        res = slack.conversations_replies(channel=channel, ts=thread_ts)
        reps = res.get("messages")
        isinthread = False
        count = 0
        history = []
        for rep in reps:
            bot = True if "bot_id" in rep else False
            text = rep.get("text", "")
            count += len(text)
            history.append([bot, text])
        if count > 32 * 1024:
            reply = '[context too large; please start a new thread]'
        else:
            reply = context_gpt(history)
        if not reply: reply = '[empty]'
        #print("[gpt]", user, reply)
        slack.chat_postMessage(channel=channel, text=reply, thread_ts=thread_ts)
    except:
        pass
    botmsg.pop(msgid)

def handle_event(evt):
    msgid = None
    try:
        authobj = evt.get("authorizations")
        self = authobj[0].get("user_id")
        evtobj = evt.get("event")
        msgid = evtobj.get("client_msg_id")
        ts = evtobj.get("ts")
        evttype = evtobj.get("type")
        channel = evtobj.get("channel")
        if evttype == "app_mention":
            user = evtobj.get("user")
            text = " ".join(re.split('<@[^@<>]+>', evtobj.get("text", ""))).strip()
            thread_ts = evtobj.get("thread_ts", None)
            if text and thread_ts is None:
                t = Thread(target=async_gpt, args=[msgid, user, text, ts, channel])
                t.run()
            elif text and thread_ts is not None:
                t = Thread(target=async_context_gpt, args=[msgid, user, text, thread_ts, channel])
                t.run()
        # bot_id = B05HZ499ACB
        elif evttype == "message" and evtobj.get("channel_type") == "im" and "bot_id" not in evtobj:
            user = evtobj.get("user")
            text = " ".join(re.split('<@[^@<>]+>', evtobj.get("text", ""))).strip()
            thread_ts = evtobj.get("thread_ts", None)
            if text and thread_ts is None:
                t = Thread(target=async_gpt, args=[msgid, user, text, ts, channel])
                t.run()
            elif text and thread_ts is not None:
                t = Thread(target=async_context_gpt, args=[msgid, user, text, thread_ts, channel])
                t.run()
        return ('ok', 200)
    except:
        return ('ok', 200)

@app.route("/bot", methods=['POST'])
def start():
    if not request.is_json: return e404()
    print(request.json)
    token = request.json.get("token")
    if token != config["SLACK_TOKEN"]: return e404()
    if request.json.get("challenge", None) is not None:
        return (request.json.get("challenge"), 200)
    else:
        return handle_event(request.json)
    return ('ok', 200)

