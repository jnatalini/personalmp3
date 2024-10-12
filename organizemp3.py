import os
import pdb
import subprocess
import json
import sys
import re
import eyed3
import requests
import csv
import urllib.parse
import urllib.request as req
from difflib import SequenceMatcher
from openai import OpenAI


def list_mp3s():
    try:
        return subprocess.check_output('ls *.mp3', shell=True,encoding='utf8').split('\n')
    except:
        return []  

def create_dir(path):
    try:
        os.makedirs(path.encode('utf-8'),exist_ok=True)
        return True
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(exc_type, exc_tb.tb_lineno)
        print(f'couldnt create dir or already existing {path}')
        return False

def move_file(mp3_array, artist, loc):
    for file in mp3_array:
        if file.strip() == '':
            continue
        if artist in file or artist == 'unknown':
            try:
                path = loc + '/%s'%artist
                dest_filename = re.sub('[^0-9a-zA-Z\.]+', '_', file)
                os.rename(loc +'/'+ file, path + '/' + dest_filename)
            except:
                print(f'coundnt move file: {file} to {dest_filename}')
                print("Unexpected error:", sys.exc_info()[0])

def process_files(mp3list):
    dict = {} 
    for file in mp3list:
        if file.strip() == '':
            continue
        try:
            audio = eyed3.load(file)
            dict[file] = {}   
            tag_obj = audio.tag  
            for method_name in attributes:
                dict[file][method_name] = str(getattr(tag_obj,method_name)) 
        except:
            dict[file] = {'album': 'None', 'artist': 'None', 'title': f'{file.split(".")[0]}', 'recording_date': 'None'} 
        if dict[file]['album'] == 'None' or dict[file]['album'] == None:
            if dict[file]['artist'] != 'None':
                album_name = get_api_data_v2(dict[file]['title'], dict[file]['artist'])
                dict[file]['album'] = album_name 
        if dict[file]['album'] == 'None' or dict[file]['album'] == None:
            try:
                title_parts = file.split('-')
                phrases = ['Official_Video', 'Official_Lyric_Video', 'Lyrics', 'Audio','Video','Official_Music_Video', 'Lyric_Video']
                for phrase in phrases:
                    title_parts = [x.replace(phrase,'') for x in title_parts]
                title_parts = [x.replace('_',' ') for x in title_parts]
                title_parts = [x.strip() for x in title_parts]
                if len(title_parts) > 1:  
                    album_name = get_api_data_v2(title_parts[0], title_parts[1])
                    #pdb.set_trace()
                    if album_name == 'None':
                        album_name = get_api_data_v2(title_parts[1], title_parts[0])
                        if album_name != 'None':
                            dict[file]['album'] = album_name
                            dict[file]['title'] = title_parts[1]
                            dict[file]['artist'] = title_parts[0]
                    else:
                        dict[file]['album'] = album_name
                        dict[file]['title'] = title_parts[0]
                        dict[file]['artist'] = title_parts[1]
            except:
                None      
    return dict                     
        
def move_files(organized, path, mainf):
    dest_loc = path + '/' + mainf + '/'
    try:  
        for art in organized.keys():
            create_dir(dest_loc + art)
            for alb in organized[art].keys():
                create_dir(dest_loc + art + '/' + alb)
                for title in organized[art][alb].keys():
                    for fname in organized[art][alb][title]: 
                        os.rename(path + '/' + fname, dest_loc + art + '/' + alb + '/' + fname)
    except:
        create_dir(dest_loc + 'None')
        os.rename(path + '/' + fname, dest_loc + 'None/'  + fname)

def move_filesv2(organized, path, mainf):
    dest_loc = path + '/' + mainf + '/'
    try:  
        for art in organized.keys():
            if art != 'None':
                create_dir(dest_loc + art)
            for alb in organized[art].keys():
                if alb != 'None':
                    create_dir(dest_loc + art + '/' + alb)
                for title in organized[art][alb].keys():
                    for fname in organized[art][alb][title]: 
                        if art != 'None':
                            if alb != 'None':
                                os.rename(path + '/' + fname, dest_loc + art + '/' + alb + '/' + fname)
                            else: # if alb is None
                                os.rename(path + '/' + fname, dest_loc + art + '/' + fname)
                        else:  #if artist is NONE
                            os.rename(path + '/' + fname, dest_loc + fname)
    except:
        create_dir(dest_loc)
        os.rename(path + '/' + fname, dest_loc + fname)


def print_metadata(organized):
    for art in organized.keys():
        print('artist: ' + art)
        for alb in organized[art].keys():
            print('-->album: ' +alb)
            for title in organized[art][alb].keys():
                print('---->title: ' + title)
                print('------> filenames: ')
                print(organized[art][alb][title]) 
    
def organize_metadata(metadata):
    organized = {}
    for fff in metadata:
        fmd = metadata[fff]
        artist = str(fmd['artist'])
        album = str(fmd['album'])
        title = str(fmd['title'])
        if artist in organized.keys():
            if album in organized[artist].keys():
                if title in organized[artist][album].keys():
                    organized[artist][album][title].append(fff)
                else:
                    organized[artist][album][title] = [fff]
            else:
                organized[artist][album]={title: [fff]}
        else:
            organized[artist] = {album: { title: [fff]}}    
    return organized


def get_api_data(song_name, artist):
    try:
        #command = f'https://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key=062fd5ff3be7b45f11ae0e507f94aa34&artist={artist}&track={song_name}&format=json'
        song_name = song_name.split('(')[0].strip()  
        command = f'https://ws.audioscrobbler.com/2.0/?method=track.getSimilar&api_key=062fd5ff3be7b45f11ae0e507f94aa34&artist={artist}&track={song_name}&format=json'
        res = requests.get(command)
        parsed_json = json.loads(res.content)   
        if 'similartracks' in parsed_json:
            return parsed_json['similartracks']['track'][0]['name']
    except:
        return 'None'

def similar_song_v2(songoriginal, possiblesong):
    s = SequenceMatcher(None, songoriginal, possiblesong)
    ratio_songs = s.ratio()
    if ratio_songs >= 0.8:
        print(f'SIMILAR {ratio_songs} {songoriginal} {possiblesong}')
        return True
    else:
        return False

def get_api_data_v2(song_name, artist):
    try:
        #command = f'https://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key=062fd5ff3be7b45f11ae0e507f94aa34&artist={artist}&track={song_name}&format=json'
        parsing = song_name.split('(')[0].strip().lower()  
        song_name = parsing.split('-')[1].strip().replace(',','').replace('&',' ').split('[')[0].split('(')[0]  
        artist = parsing.split('-')[0].strip().split('&')[0].strip() 
        #command = f'https://ws.audioscrobbler.com/2.0/?method=track.getSimilar&api_key=062fd5ff3be7b45f11ae0e507f94aa34&artist={artist}&track={song_name}&format=json'
        command = f'https://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key=062fd5ff3be7b45f11ae0e507f94aa34&artist={req.pathname2url(artist)}&track={req.pathname2url(song_name)}&format=json'
        res = requests.get(command)
        parsed_json = json.loads(res.content) 
        if 'track' in parsed_json:
            if similar_song_v2(song_name.lower(), parsed_json['track']['name'].replace(',', '').lower()):
                if 'album' in parsed_json['track']:
                    return parsed_json['track']['album']['title']
              
    except:
        return 'None'


def get_info(row):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"this is a song name: {row['title']}. This is possibly the artist  of the song: {row['artist']}, but it may not be accurate. Based on this information, find the artist, album and song title. Provide the response in json format, with fields 'Artist', 'Album' and 'Title'. If you cannot find it return None for each field. Only include the json response, without any additional text."
            }
        ]
    )
    return completion.choices[0].message.content


def update_metadata(filenamepath, metadata):
    try:
        audio = eyed3.load(filenamepath)
        audio.tag.album = metadata['Album']
        audio.tag.artist = metadata['Artist']
        audio.tag.album_artist = metadata['Artist']
        audio.tag.title = metadata['Title']
        audio.tag.save()
    except Exception as e:
        print(e)

def refine_metadata(metadata):
    main_path = os.getcwd()
    for song in metadata:
        try:
            response = get_info(metadata[song])
            json_response = json.loads(response[8:].replace('\n', ' ').replace('```',''))
            print(json_response)
            if json_response['Artist'] != None: 
                filepath = os.path.join(main_path, song)
                update_metadata(filepath, json_response)
        except Exception as e:
            print(e)

attributes = ['album',
              'artist',
              'title',
              'recording_date']

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
client = OpenAI()
mp3_array = list_mp3s()
metadata = process_files(mp3_array)
refine_metadata(metadata)
metadata = process_files(mp3_array)
organized = organize_metadata(metadata)
#print_metadata(organized)
#move_files(organized, __location__ , '/music_org/')   
move_filesv2(organized, __location__ , '/music_org/')   
print(f'{len(organized)} artists processed')

#Done -- try to organize the files, group them together
#TODO: create folder for artist if it doesnt exist
#TODO: create subfolder for album if it doesnt exist
#TODO: move song inside album 
#TODO delete song
#TODO: if None artist, album, song move it to unknown
#export OPENAI_API_KEY="your_api_key_here"
