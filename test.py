from twilio.rest import Client

account_sid = 'AC259ca8d67beca82b2aff9a231ad6ff83'
auth_token = 'b35b4abd8dce8340c9494dedbaea75d2'
client = Client(account_sid, auth_token)

message = client.messages.create(
  from_='whatsapp:+14155238886',
  body='Your appointment is coming up on July 21 at 3PM',
  to='whatsapp:+19046086893'
)

print(message.sid)