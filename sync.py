from pyicloud import PyiCloudService, exceptions
import os
from scuapi import API
import time

url = "https://streamingcommunity.buzz/titles/7449-teenage-mutant-ninja-turtles-tartarughe-ninja"
sc = API("streamingcommunity.buzz")
res = sc.load(url)

path = f"content/{res['name']}/"
if not os.path.exists(path):
    os.makedirs(path)
os.chdir(path)

api = PyiCloudService('giulio030208@icloud.com', 'Bud1nazz@')

if api.requires_2fa:
  print("Two-factor authentication required.")
  code = input("Enter the code you received of one of your approved devices: ")
  result = api.validate_2fa_code(code)
  print("Code validation result: %s" % result)

  if not result:
      print("Failed to verify security code")
      sys.exit(1)

  if not api.is_trusted_session:
      print("Session is not trusted. Requesting trust...")
      result = api.trust_session()
      print("Session trust result %s" % result)

      if not result:
          print("Failed to request trust. You will likely be prompted for the code again in the coming weeks")
elif api.requires_2sa:
  import click
  print("Two-step authentication required. Your trusted devices are:")

  devices = api.trusted_devices
  for i, device in enumerate(devices):
      print(
          "  %s: %s" % (i, device.get('deviceName',
          "SMS to %s" % device.get('phoneNumber')))
      )

  device = click.prompt('Which device would you like to use?', default=0)
  device = devices[device]
  if not api.send_verification_code(device):
      print("Failed to send verification code")
      sys.exit(1)

  code = click.prompt('Please enter validation code')
  if not api.validate_verification_code(device, code):
      print("Failed to verify verification code")
      sys.exit(1)

pathname = "Streaming Community"

if not pathname in api.drive.dir():
    api._drive.params["clientId"] = api.client_id
    api.drive.mkdir(pathname)
    while not pathname in api.drive.dir():
        api = PyiCloudService('giulio030208@icloud.com', 'Bud1nazz@')
        time.sleep(1)

if not res["name"] in api.drive[pathname].dir():
    api._drive.params["clientId"] = api.client_id
    api.drive[pathname].mkdir(f"{res['name']}")
    while not res["name"] in api.drive[pathname].dir():
        api = PyiCloudService('giulio030208@icloud.com', 'Bud1nazz@')
        time.sleep(1)

downloaded_files = os.listdir("./")
print("Starting to upload!")
for i in downloaded_files:
    if not i in api.drive[pathname][res["name"]].dir():
        prevdir = os.getcwd()
        while not i in api.drive[pathname][res["name"]].dir():
            try:
              with open(i, "rb") as f:
                  api.drive[pathname][res["name"]].upload(f)
              api = PyiCloudService('giulio030208@icloud.com', 'Bud1nazz@')
            except exceptions.PyiCloudAPIResponseException:
              api = PyiCloudService('giulio030208@icloud.com', 'Bud1nazz@')
                
    print(f"Finished to upload {i}")