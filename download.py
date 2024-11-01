import asyncio
from concurrent.futures import ThreadPoolExecutor
import sys
import requests as r
import os
from pyicloud import PyiCloudService
import yt_dlp
from scuapi import API
import json
from typing import List, Dict, TypedDict
from pyicloudcustom import cloudMakeDirs, cloudNestedDir, getApi, upload

pathname = "Streaming Community"

class EpisodeData(TypedDict):
    season: int
    episode: int
    title: str
    url: str
    
class EntryData(TypedDict):
    name: str
    url: str
    isMovie: bool
    totalEpisodes: int | None
    episodes: List[EpisodeData] | None
    year: int
    MovieIsOnCloud: bool =  False

def filename(entry: EntryData, episode: EpisodeData | None, isMovie: bool) -> str:
    if not isMovie:
        with yt_dlp.YoutubeDL() as ydl:
            ext = ydl.extract_info(episode["url"], download = False)["ext"]
            return f"{entry['name']} - {zfill(entry, episode)} - {episode['title']}.{ext}".replace(":", " -")
    else:
        with yt_dlp.YoutubeDL() as ydl:
            info = ydl.extract_info(entry["url"], download = False)
            with open(f"metadata.json", 'w') as f:
                f.write(json.dumps(info, indent = 4))
            return f"{entry['name']} ({entry['year']}) {info['formats'][-1]['height']}p.{info['ext']}".replace(":", " -")

def makeEpisodes(res: dict) -> List[EpisodeData]:
    return [{
        "season": ep["season"], 
        "episode": ep["episode"], 
        "title": ep["name"],
        "url": ep["url"],
    } for i, ep in enumerate(res["episodeList"])]

def makeEntry(res: dict) -> EntryData:
    data = None
    isMovie = res["type"] == "Movie"
    if isMovie:
        data = EntryData(name = res["name"], url = res["url"], isMovie=isMovie, totalEpisodes = None, episodes = None, year=res["year"])
    else:
        episodes = makeEpisodes(res)
        data = EntryData(name = res["name"], url = res["url"], isMovie=isMovie, totalEpisodes = len(res["episodeList"]), episodes = episodes, year=res["year"])
    return data

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

def download(entry: EntryData, episodes: List[EpisodeData] | None, path: str):
    makeDirsUnlessExists(path)
    if not entry["isMovie"]:
        for ep in episodes:
            with yt_dlp.YoutubeDL({
                "outtmpl": os.path.join(path, filename(entry, ep, isMovie=entry["isMovie"])),
                "concurrent_fragment_downloads": 5,
                "fragment_retries": 10
            }) as yld:
                yld.download([ep["url"] for ep in episodes])
    else: 
        with yt_dlp.YoutubeDL({
            "outtmpl": os.path.join(path, filename(entry, None, isMovie=entry["isMovie"])),
            "concurrent_fragment_downloads": 10,
            "fragment_retries": 10
        }) as yld:
            yld.download([entry["url"]]) 

def removeEpisode(entry: EntryData, episode: EpisodeData, path: str):
    #lib = read()
    #new_episodes = [ep for ep in lib[entry["name"]]["episodes"] if ep["url"] != episode["url"]]
    #lib[entry["name"]]["episodes"] = new_episodes
    #if lib[entry["name"]]["episodes"] == []:
    #    lib -= {entry['name']: entry}
   # save(lib)
    os.remove(f"{path}/{filename(entry, episode, isMovie=entry['isMovie'])}")

def whatIsOnTheCloud(api: PyiCloudService, path: str, entry: EntryData) -> EntryData:
    onCloud = cloudNestedDir(api, path).dir()
    if entry["isMovie"]:
        if filename(entry, None, isMovie=entry['isMovie']) not in onCloud:
            entry["MovieIsOnCloud"] = False
        else: 
            entry['MovieIsOnCloud'] = True
        return entry
    else:
        indexes = [episode.replace(f"{entry['name']} - S", "").split(" - ")[0] for episode in onCloud]
        episodes = []
        for i in indexes:
            season, episode = i.split("E")
            rightEpisode = [ep for ep in entry["episodes"] if ep["season"] == int(season) and ep["episode"] == int(episode)][0]
            ep = EpisodeData(season=int(season), episode=int(episode), title=str(rightEpisode["title"]), url=rightEpisode["url"])
            episodes.append(ep)
        return episodes

def downloadBigBro(entry: EntryData, episode: EpisodeData | None, path: str):
    fname = filename(entry, episode, entry['isMovie'])
    download(entry, [episode], f"content/{path}")
    upload(os.path.join(f"content/{path}", fname), f"Streaming Community/{path}")
    os.remove(os.path.join(f"content/{path}", fname))

def getOnTheDamnCloudThenFuckOff(entry: EntryData, episodes: List[EpisodeData] | None, path: str):
    cloudpath = f"Streaming Community/{path}"
    api = getApi()
    cloudMakeDirs(api, cloudpath)
    cloud = whatIsOnTheCloud(api, cloudpath, entry)
    if entry["isMovie"] and entry["MovieIsOnCloud"]:
        print("Movie is already on cloud")
    elif entry["isMovie"] and not entry["MovieIsOnCloud"]:
        downloadBigBro(entry, None, path)
    elif not entry["isMovie"]:
        inCloud = [ep for ep in episodes if ep in cloud]
        for ep in inCloud:
            print(f"S{ep['season']}E{ep['episode']} already on cloud")
        episodes = [ep for ep in episodes if ep not in cloud]
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = []
            for episode in episodes:
                futures.append(pool.submit(downloadBigBro, entry, episode, path))
            for future in futures:
                future.result()

async def main():
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    sc = API("streamingcommunity.computer")
    url = sys.argv[1]
    res = sc.load(url)

    entry = makeEntry(res)
    if entry['isMovie']:
        getOnTheDamnCloudThenFuckOff(entry, None, '')
    elif not entry['isMovie']:
        episodes = makeEpisodes(res)
        getOnTheDamnCloudThenFuckOff(entry, episodes, entry['name'])
        
asyncio.run(main())