#from math import e
from pyicloud.base import DriveService
import requests as r
import bs4
from session import session
import os
from pyicloud import PyiCloudService, exceptions
import sys
import time
import yt_dlp
from scuapi import API
import json
from typing import List, Dict, TypedDict, Tuple
from functools import reduce
import operator

libraryPathname= "library.json"
pathname = "Streaming Community"
url = "https://streamingcommunity.computer/titles/7449-teenage-mutant-ninja-turtles-tartarughe-ninja"


class EpisodeData(TypedDict):
    season: int
    episode: int
    title: str
    url: str
    
class EntryData(TypedDict):
    name: str
    url: str
    totalEpisodes: int
    episodes: List[EpisodeData]

Library = Dict[str, EntryData]

def filename(entry: EntryData, episode: EpisodeData) -> str:
    with yt_dlp.YoutubeDL() as ydl:
        ext = ydl.extract_info(episode["url"], download = False)["ext"]
        return f"{entry['name']} - {zfill(entry, episode)} - {episode['title']}.{ext}"

def makeEpisodes(res: dict) -> List[EpisodeData]:
    return [{
        "season": ep["season"], 
        "episode": ep["episode"], 
        "title": ep["name"],
        "url": ep["url"],
    } for ep in res["episodeList"]]

def makeEntry(res: dict) -> EntryData:
    return EntryData(name = res["name"], url = res["url"], totalEpisodes = len(res["episodeList"]), episodes = episodes)

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

def verifyLibrary():
    if not os.path.exists(libraryPathname):
        print(f"{libraryPathname} not found, creating...")
        with open(libraryPathname, "w") as f:
            f.write("{}")

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

def read() -> Library:
    verifyLibrary()
    with open(libraryPathname) as f:
        return json.loads(f.read())

def save(library: Library):
    verifyLibrary()
    with open(libraryPathname, "w") as f:
        f.write(json.dumps(library, indent = 4))

def zfill(entry: EntryData, episode: EpisodeData):
    zfill = 0
    for ep in entry[r"episodes"]:
        if len(str(ep["episode"])) > zfill:
            zfill = len(str(ep["episode"]))
    return f"S{str(episode['season']).zfill(zfill)}E{str(episode['episode']).zfill(zfill)}"

def makeDirsUnlessExists(path: str):
    if not os.path.exists(path):
        os.makedirs(path)

def makeDirsUnlessExistsThenChdir(path: str):
    makeDirsUnlessExists(path)
    os.chdir(path)

def upload(entry: EntryData, episodes: List[EpisodeData], path: str, uploadPath: str, api: PyiCloudService):
    cloudMakeDirs(api, uploadPath)
    prev = os.getcwd()
    makeDirsUnlessExistsThenChdir(path)
    if path not in cloudNestedDir(api, uploadPath).dir():
        for episode in episodes:
            while filename(entry, episode) not in cloudNestedDir(api, uploadPath).dir():
                try:
                    print(f"Trying to upload {zfill(entry, episode)}")
                    with open(filename(entry, episode), "rb") as f:
                        cloudNestedDir(api, uploadPath).upload(f)
                    break
                except exceptions.PyiCloudAPIResponseException:
                    print(f"failed, retrying {zfill(entry, episode)}")
                    api = getApi()
            os.chdir(prev)
            lib = read()
            lib[entry["name"]]["episodes"].append(episode)
            save(lib)
            makeDirsUnlessExistsThenChdir(path)
            print(f"Finished uploading {zfill(entry, episode)}")
    os.chdir(prev)

def download(entry: EntryData, episodes: List[EpisodeData], path: str):
    prev = os.getcwd()
    makeDirsUnlessExistsThenChdir(path)
    for ep in episodes:
        with yt_dlp.YoutubeDL({
            "outtmpl": filename(entry, ep)
        }) as yld:
            yld.download([ep["url"] for ep in episodes])
    os.chdir(prev)

def removeEpisode(entry: EntryData, episode: EpisodeData, path: str):
    #lib = read()
    #new_episodes = [ep for ep in lib[entry["name"]]["episodes"] if ep["url"] != episode["url"]]
    #lib[entry["name"]]["episodes"] = new_episodes
    #if lib[entry["name"]]["episodes"] == []:
    #    lib -= {entry['name']: entry}
   # save(lib)
    os.remove(f"{path}/{filename(entry, episode)}")

def whatIsOnTheCloud(api: PyiCloudService, path: str, entry: EntryData) -> List[EpisodeData]:
    list = cloudNestedDir(api, path).dir()
    indexes = [episode.replace(f"{entry['name']} - S", "").split(" - ")[0] for episode in list]
    episodes = []
    for i in indexes:
        season, episode = i.split("E")
        rightEpisode = {}
        for ep in entry["episodes"]:
            episodeInEntry = int(ep["episode"])
            seasonInEntry = int(ep["season"])
            isRightEp = episodeInEntry == int(episode)
            isRightSeason = seasonInEntry == int(season)
            if isRightEp and isRightSeason:
                rightEpisode = ep
        url: str = rightEpisode["url"]
        title: str = rightEpisode["title"]
        ep = EpisodeData(season=int(season), episode=int(episode), title=str(title), url=url)
        episodes.append(ep)
    return episodes

def getOnTheDamnCloudThenFuckOff(entry: EntryData, episodes: List[EpisodeData], path: str, api: PyiCloudService):
    cloudpath = f"Streaming Community/{path}"
    cloudMakeDirs(api, cloudpath)
    api = getApi()
    cloud = whatIsOnTheCloud(api, cloudpath, entry)
    episodes = [ep for ep in episodes if ep not in cloud]
    for episode in episodes:
        download(entry, [episode], f"content/{path}")
        upload(entry, [episode], f"content/{path}", f"Streaming Community/{path}", api)
        removeEpisode(entry, episode, f"content/{path}")

api = getApi()
sc = API("streamingcommunity.computer")
res = sc.load(url)

episodes = makeEpisodes(res)
entry = makeEntry(res)

downloaded = read()
save(downloaded | {entry["name"]: entry})
missing_episodes = [ep for ep in episodes if ep not in downloaded[entry["name"]]["episodes"]]
getOnTheDamnCloudThenFuckOff(entry, episodes, entry['name'], api)

makeDirsUnlessExists(f"content/{entry['name']}")