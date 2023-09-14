# gpt4slack
gpt integration with slack

### What the bot do

- if @ in a channel, reply as a thread
- if send message in DM, reply as a thread
- if chat in a thread, using whole thread as context and reply in the thread

```
# edit .env
SLACK_TOKEN=<token>
SLACK_REPLY_CHANNEL_TOKEN=<bot_token>
GPT_ORG=<gpt_org_id>
GPT_KEY=<gpt_key>

# run index.py
flask --app index.py run --host 127.0.0.1 --port 8080
# wrap it with nginx to serve https at 443
# fill https://<domain> in slack config and verify the url
```

bot scope:
- `app_mentions:read`: if you want the bot be @ and it can reply
- `chat:write`: if you want to enable DM bot
- `im:history`
- `mpim:history`

### How to add your prompt

In the code
```
... messages=[{ ... }, ...]
```
you need to add first message as a prompt like:
```
messages = [{ role: 'system', content: prompt } ...]
```

### How to let gpt provide defined json format output

besides `messages`, add keys:
```
   messages: [...],
   functions: [{ name: 'jsonify', parameters: param }],
   function_call: { name: 'jsonify' }
```

you need to define json format in `param` like:
```
   type: 'object',
   properties: {
      company_entities: {
         type: 'array',
         items: {
            type: 'object',
            properties: {
               name: {
                  type: 'string',
                  minLength: 2,
                  maxLength: 100,
                  description: 'the name of entity',
               },
            },
         },
         description: 'all named entities extracted from the input text',
      },
   },
```

and in your `prompt` you can ask gpt to call `jsonify` to parse result.
then you can get formated result at for example `.choices[0].message.function_call.arguments`
