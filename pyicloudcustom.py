from pyicloud import PyiCloudService, exceptions
from pyicloud.base import DriveService
from functools import reduce
import operator
import sys
from typing import List

def getApi():
    api = PyiCloudService('giulio030208@icloud.com', 'Bud1nazz@')
    verifyApi(api)
    api.drive.dir()
    api._drive.params["clientId"] = api.client_id
    return api
    
def verifyApi(api):
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

def cloudMakeDirs(api: PyiCloudService, path: str):
    parts = path.strip('/').split('/')
    done = []
    for part in parts:
        cloudNestedDir(api, done).mkdir(part)
        while part not in cloudNestedDir(api, done).dir():
            api = getApi()
            cloudNestedDir(api, done).mkdir(part)
        done.append(part)

def cloudNestedDir(api: PyiCloudService, path: str | List[str]) -> DriveService:
    if type(path) is str: 
        parts = path.strip("/").split("/")
    else:
        parts = path                  
    return reduce(operator.getitem, parts, api.drive)

def upload(path: str, uploadPath: str, api: PyiCloudService):
    api = getApi()
    cloudMakeDirs(api, uploadPath)
    if path not in cloudNestedDir(api, uploadPath).dir():
            while path not in cloudNestedDir(api, uploadPath).dir():
                try:
                    print(f"Trying to upload {path}")
                    try: 
                        with open(path,) as f:
                            cloudNestedDir(api, uploadPath).upload(f)
                    except UnicodeDecodeError:
                        with open(path, 'rb') as f:
                            cloudNestedDir(api, uploadPath).upload(f)
                    except Exception as e:
                        print(e)
                    break
                except exceptions.PyiCloudAPIResponseException:
                    print(f"failed, retrying {path}")
                    api = getApi()
            print(f"Finished uploading {path}")