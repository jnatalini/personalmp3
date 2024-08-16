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
import shutil
import pandas as pd
import datetime
import numpy


def process_files(mp3list, attributes):
    dict = {} 
    for file in mp3list:
        print(f'processing: {file}\n')  
        if file.strip() == '':
            continue
        # try to find info in metatags
        try:
            audio = eyed3.load(file)
            dict[file] = {}   
            tag_obj = audio.tag  
            for method_name in attributes:
                dict[file][method_name] = str(getattr(tag_obj, method_name)) 
            #print(dict)   
        except:
            dict[file] = {'album': 'None', 'artist': 'None', 'title': f'{file.split(".")[0]}', 'recording_date': 'None'} 

        # continue processing without album information 
        if dict[file]['album'] == 'None' or dict[file]['album'] == None:
            try:
                title_parts = file.split('-')
                phrases = ['Official_Music','Official_Video', 'Official_Lyric_Video', 'Lyrics', 'Audio','Video','Official_Music_Video', 'Lyric_Video']
                for phrase in phrases:
                    title_parts = [x.replace(phrase,'') for x in title_parts]
                title_parts = [x.replace('_',' ') for x in title_parts]
                title_parts = [x.strip() for x in title_parts]
                if len(title_parts) > 1:  
                    album_name = 'None'
                    #album_name = get_api_data_v2(title_parts[0], title_parts[1])
                    album_name = 'None'
                    #pdb.set_trace()
                    if album_name == 'None':
                        album_name = 'None'
                        #album_name = get_api_data_v2(title_parts[1], title_parts[0])
                        album_name = 'None'
                        dict[file]['album'] = album_name
                        dict[file]['title'] = title_parts[1]
                        dict[file]['artist'] = title_parts[0].split('/')[-1]
                    else:
                        dict[file]['album'] = album_name
                        dict[file]['title'] = title_parts[0].split('/')[-1]
                        dict[file]['artist'] = title_parts[1]
            except:
                None      
    return dict                     



'''
Final list mp3, works for a full path
'''
def imp_list_mp3(path):
    try:
        res = []
        for (dir_path, dir_names, file_names) in os.walk(path):
            for filename in file_names:
                res.append(dir_path + '/' + filename)
        return res
    except:
        return []


def mp3_reader(source_directory, output_filename, delimiter):
    attbs = ['album',
                'artist',
                'title',
                'recording_date']

    mp3_array = imp_list_mp3(source_directory)
    metadata = process_files(mp3_array, attbs)

    #'path': 'album': 'None', 'artist': 'Aerosmith', 'title': 'Amazing', 'recording_date': '2009-12-24', 'data_curated', 'data_updated'}
    dict = {'path':[],
            'album':[],
            'artist':[],
            'title':[],
            'data_curated':[],
            'data_updated':[]
        }

    df = pd.DataFrame(dict)
    for key in metadata.keys():
        album = '' if metadata[key]['album'] == 'None' else metadata[key]['album']
        artist = '' if metadata[key]['artist'] == 'None' else metadata[key]['artist']
        title = '' if metadata[key]['title'] == 'None' else metadata[key]['title']
        row=[key, album, artist, title, '', '']
        df.loc[len(df.index)] = row
    df.to_csv(output_filename, sep=delimiter, index=False)


def has_filename(filename, arrayofsongs):
    for element in arrayofsongs:
        if filename in element['filename']:
            return True
    return False

def read_file_v3(filename, delim):
#0@1@2@3@4    
#path@album@artist@title@data_curated@data_updated
    output = {}
    try:
        with open(filename, newline='', encoding='utf-8') as f:
            reader = csv.reader(f,delimiter = delim)
            for row in reader:
                arow = row 
                if arow[2] in output:
                    if not has_filename(arow[0], output[arow[2]]): 
                        output[arow[2]].append({ 'filename': arow[0], 'artist': arow[2], 'album': arow[1] , 'title': arow[3]})
                else:
                    output[arow[2]] = [{ 'filename': arow[0], 'artist': arow[2], 'album': arow[1], 'title': arow[3] }]
        return output   
    except:
        return output



def matchingString(x, y):
    match=''
    for i in range(0,len(x)):
        for j in range(0,len(y)):
            k=1
            # now applying while condition untill we find a substring match and length of substring is less than length of x and y
            while (i+k <= len(x) and j+k <= len(y) and x[i:i+k]==y[j:j+k]):
                if len(match) <= len(x[i:i+k]):
                   match = x[i:i+k]
                k=k+1
    return match  


def contained(source_str, dest_str):
    matching = matchingString(source_str.lower(), dest_str.lower())
    if source_str.lower() in matching.lower():
        return True
    else:
        return False 

'''
This method groups artist into a dictionary of arrays, for example
'Roxette': ['Roxette, Per Gessle'],
'''
def create_artist_dict(artist_array):
    dict = {}
    sorter_arr = sorted(artist_array, key=len)
    for artist in sorter_arr:
        if artist not in dict:
            found = False
            for key in dict.keys():
                #if key in artist:
                if contained(key, artist):
                    dict[key].append(artist)
                    found = True
                    break
            if not(found):
                dict[artist] = []
    return dict  




"""Moves a file from one location to another.

  Args:
    source_file: The path to the source file.
    destination_file: The path to the destination file.
"""
def actual_move_file(source_file, destination_file):

  # Check if the source file exists.
  if not os.path.exists(source_file):
    raise FileNotFoundError(f"The source file '{source_file}' does not exist.")

  # Check if the destination directory exists.
  destination_dir = os.path.dirname(destination_file)

  if not os.path.exists(destination_dir):
    os.makedirs(destination_dir)

  # Move the file.
  os.rename(source_file, destination_file)
    



def remove_empty_directories(path):
  """Recursively removes empty directories from the given path."""

  for root, directories, files in os.walk(path, topdown=False):
    for directory in directories:
      fullpath = os.path.join(root, directory)
      if not os.listdir(fullpath):
        os.rmdir(fullpath)

'''
Move mp3 files with the new structure
input: new dictionary original dictionary
'''
def move_files(consolidated_artist, dictionary, destination_path):
    for key in consolidated_artist:
        try:
            #print('Main Artist = ' + key)
            arr = consolidated_artist[key]
            if key == '':
                break
            arr.append(key)
            for artist in arr:
                for song in dictionary[artist]:
                    #TODO: do the actual moving of the files from 
                    # song['filename'] to /destination/key/song['album']/title
                    song_filename = song['filename'].split('/')[-1]
                    destination = destination_path + '/' + key + '/'
                    if song['album'] != 'None':
                        destination = destination +  song['album'] + '/'
                    destination = destination + song_filename   
                    #pdb.set_trace()
                    #print(song['filename']) 
                    #print(destination)
                    #print('--------------\n')
                    try:  
                        actual_move_file(song['filename'], destination)
                    except Exception as err:
                        print('Error with: ' + song['filename'] + "\n")
                        print(err)
        except Exception as e: 
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            continue         

# returns a dataframe with the format of source_file, containing album info.
def process_files2(source_file, album_file, source_delimiter=',', album_delimiter=','):
    df_source = pd.read_csv(source_file, sep=source_delimiter)
    df_album = pd.read_csv(album_file, sep=album_delimiter)
    df_source = df_source.replace(numpy.nan, '')
    df_album = df_album.replace(numpy.nan, '')

    for index,row in df_album.iterrows():
        desired_row = df_source.loc[df_source['path'] == row['path']]
        if not desired_row.empty and desired_row['data_curated'].values[0]=='':
            df_source.loc[df_source['path'] == row['path'],'album'] = row['album']
            df_source.loc[df_source['path'] == row['path'],'data_curated'] = 'TRUE'
            df_source.loc[df_source['path'] == row['path'],'data_updated'] = str(datetime.datetime.now())
    return df_source
        

#returns the rows unprocessed
def return_unprocessed(source_dataframe):
    indexRes = source_dataframe[ (source_dataframe['data_curated'] == True) ].index
    source_dataframe.drop(indexRes , inplace=True)
    return source_dataframe

def load_df(path):
    return pd.read_csv(path)



def update_file_metadata(mp3list, data_df):
    for file in mp3list:
        print(f'processing: {file}\n')  
        if file.strip() == '':
            continue
        # try to find info in metatags
        try:
            if not data_df.loc[data_df['path'] == file].empty:
                row = data_df.loc[data_df['path'] == file]
                if row['data_curated'].values[0] == True:
                    audio = eyed3.load(file)
                    if not audio.tag:
                        audio.initTag()
                    audio.tag.album = row['album'].values[0]
                    audio.tag.artist = row['artist'].values[0] 
                    audio.tag.album_artist = row['artist'].values[0]
                    audio.tag.title = row['title'].values[0]
                    audio.tag.save()
        except Exception as e: 
            print(e)
            continue 


def find_comment(artist, comments_df):
    comments = comments_df.loc[comments_df['artist'] == artist]['comments']
    if comments.empty or pd.isna(comments).values[0]:
        return ''
    else:
        return comments.values[0]

def update_file_comments(mp3list, data_df, comments_df):
    for file in mp3list:
        print(f'processing: {file}\n')
        if file.strip() == '':
            continue
        # try to find info in metatags
        try:
            if not data_df.loc[data_df['path'] == file].empty:
                row = data_df.loc[data_df['path'] == file]
                comment_result = find_comment(row['artist'].values[0], comments_df)
                if row['data_curated'].values[0] == True:
                    audio = eyed3.load(file)
                    if not audio.tag:
                        audio.initTag()
                    
                    if comment_result=='':
                        audio.tag.comments.set(row['artist'].values[0])
                    else:
                        audio.tag.comments.set(comment_result)
                    audio.tag.album = row['album'].values[0]
                    audio.tag.artist = row['artist'].values[0]
                    audio.tag.album_artist = row['artist'].values[0]
                    audio.tag.title = row['title'].values[0]
                    audio.tag.save()
        except Exception as e:
            print(e)
            try:
                audio.tag.save()
            except Exception as e:
                continue            
            continue


def read_metadata(mp3list):
    attbs = ['album',
            'artist',
            'title',
            'recording_date']
    dict = {} 
    for file in mp3list:
        if file.strip() == '':
            continue
        try:
            audio = eyed3.load(file)
            dict[file] = {}   
            tag_obj = audio.tag  
            for method_name in attbs:
                dict[file][method_name] = str(getattr(tag_obj, method_name))
            dict[file]['comments'] = str(tag_obj.comments[0].text)
        except:
                dict[file] = {'album': 'None', 'artist': 'None', 'title': f'{file.split(".")[0]}', 'recording_date': 'None', 'comments': 'None'}
    return dict


def organize_metadata(metadata):
    organized = {}
    for fff in metadata:
        fmd = metadata[fff]
        artist = str(fmd['artist'])
        album = str(fmd['album'])
        title = str(fmd['title'])
        comments = str(fmd['comments'])
        if artist in organized.keys():
            if album in organized[artist].keys():
                if title in organized[artist][album].keys():
                    organized[artist][album][title].append(fff)
                else:
                    organized[artist][album][title] = [fff]
            else:
                organized[artist][album]={title: [fff]}
        else:
            organized[artist] = {album: { title: [fff]}, 'comments': comments}
    return organized



def create_dir(path):
    try:
        os.makedirs(path.encode('utf-8'),exist_ok=True)
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(exc_type, exc_tb.tb_lineno) 
        print(f'couldnt create dir or already existing {path}')

def move_filesv2(organized, path):
    dest_loc = path + '/'
    try:  
        for art in organized.keys():
            if art != 'None':
                if art != organized[art]['comments']:
                    art_path = organized[art]['comments'] + '/' + art
                else:
                    art_path = art
                create_dir(dest_loc + art_path)
            for alb in organized[art].keys():
                if alb == 'comments':
                    continue
                if alb != 'None' and art != 'None':
                    create_dir(dest_loc + art_path + '/' + alb)
                for title in organized[art][alb].keys():
                    for fname in organized[art][alb][title]: 
                        filename = fname.split('/')[-1]
                        if art != 'None':
                            if alb != 'None':
                                os.rename(fname, dest_loc + art_path + '/' + alb + '/' + filename)
                            else: # if alb is None
                                os.rename(fname, dest_loc + art_path + '/' + filename)
                        else:  #if artist is NONE
                            os.rename(fname, dest_loc + filename)
    except:
        try:
            create_dir(dest_loc)
            os.rename(fname, dest_loc + filename)
        except:
            print(f"couldn't create file {dest_loc + filename}")





def meta_update_metadata(source_file, source_directory):
    #load data in dataframe
    source_df = load_df(source_file)
    #read directory
    mp3_array = imp_list_mp3(source_directory)
    #for element in directory
        #if element path in dataframe, update 
    update_file_metadata(mp3_array, source_df)

def meta_move_files_v1(source_directory, destination_directory):
    mp3_array = imp_list_mp3(source_directory)
    metadata = read_metadata(mp3_array)
    organized = organize_metadata(metadata)
    move_filesv2(organized, destination_directory)   


def meta_read_commas(source_directory, output_filename):
    delimiter = ','
    mp3_reader(source_directory, output_filename, delimiter)

def meta_move_files(filename, dest_path):
    delimiter = ','
    dictionary_file = read_file_v3(filename, delimiter)
    arr = []
    for key in dictionary_file.keys(): arr.append(key)
    consolidated_artist = create_artist_dict(arr)
    print(consolidated_artist)
    # Now create a method that organizes files based on the dictionary produced by create_artist_dict
    move_files(consolidated_artist, dictionary_file, dest_path)
    #pdb.set_trace()
    #deleting empty source directory could be dangerous
    main_folder = ('/').join(dictionary_file[[*consolidated_artist][0]][0]['filename'].split('/')[0:-3])
    #pdb.set_trace()
    remove_empty_directories(main_folder)
    #pdb.set_trace()

def update_comments(source_file, source_directory, source_metadata):
    #load data in dataframe
    source_df = load_df(source_file)
    #read directory
    mp3_array = imp_list_mp3(source_directory)
    #for element in directory
    #if element path in dataframe, update
    metadata_df = load_df(source_metadata)
    update_file_comments(mp3_array, source_df, metadata_df)

#############################################
##sys.argv[1] == operation, ex: read, consolidate
if sys.argv[1] == 'read':
    ##Sys.argv[2] = source directory of the songs
    ##sys.argv[3] = source directory of songs info
    # mp3_metadata.csv is the output information
    source_directory = sys.argv[2]
    output_filename = f"{sys.argv[3]}/mp3_metadata.csv"
    delimiter = '@'
    mp3_reader(source_directory, output_filename, delimiter)
elif sys.argv[1] == 'read_commas':
    ##Sys.argv[2] = source directory of the songs
    ##sys.argv[3] = source directory of songs info
    # mp3_metadata.csv is the output information
    source_directory = sys.argv[2]
    output_filename = f"{sys.argv[3]}/mp3_metadata.csv"
    meta_read_commas(source_directory, output_filename)
elif sys.argv[1] == 'move_files':
    ##Sys.argv[2] = source filename containing final list of songs to consolidate
    ##Sys.argv[3] = destination path
    filename = f"{sys.argv[2]}"
    dest_path = f"{sys.argv[3]}"
    meta_move_files(filename, dest_path)
elif sys.argv[1] == 'consolidate_album_info':
    ##From the other algorithm
    ## argv[2] source file
    ## arvg[3] album info
    ## output: adding the album information into the source file info (output to to_reprocess.csv)
    source_filename = sys.argv[2]
    album_info = sys.argv[3]

    df_result = process_files2(source_filename, album_info, album_delimiter='@')

    df_result.to_csv(f"{sys.argv[2]}", index=False, mode='w+')

    df_reprocess = return_unprocessed(df_result)
    df_reprocess.to_csv("/".join(sys.argv[2].split('/')[0:-1])+"/to_reprocess.csv", index=False, mode='w+') 
elif sys.argv[1] == 'update_metadata':
    #python3 mp3writer.py ~/Music/songsyt0822_1/ ~/Music/mp3_metadata.csv
    ##params
    ##2: source folder
    ##3: source data file path
    source_directory = sys.argv[2]
    source_file = sys.argv[3]
    meta_update_metadata(source_file, source_directory)
elif sys.argv[1] == 'move_files_v1':
    #python3 mp3organize.py /home/jose/sambashare/Music/songsyt/songs_yt_f/songsty_1022/ /home/jose/sambashare/Music/songsyt/songs_yt_final
    #param2: source dir
    #param3: dest dir "it will also create music_og, under the dest

    # parameters:
    #sys.argv[2] source location
    #sys.argv[3] destination
    source_directory = sys.argv[2]
    destination_directory = sys.argv[3]
    meta_move_files_v1(source_directory, destination_directory)
elif sys.argv[1] == 'final_stages':
    #update_metadata
    source_directory = sys.argv[2]
    source_file = sys.argv[3]
    destination_directory = sys.argv[4]
    final_directory = sys.argv[5]
    meta_update_metadata(source_file, source_directory)
    print('update_metadata')
    #move_files_v1
    meta_move_files_v1(source_directory, destination_directory)
    print('move_files_v1')
    ''' Step 6 is unreliable 
    #read_commas
    output_filename = f"{destination_directory}/mp3_metadata.csv"
    meta_read_commas(destination_directory, output_filename)
    print('read_commas')
    #move_files
    meta_move_files(output_filename, final_directory)
    print('move_files')
    '''
elif sys.argv[1] == 'update_comments':
    ##params
    #2: source folder
    #3: source data file path
    #4: source metadata for comments
    source_directory = sys.argv[2]
    source_file = sys.argv[3]
    source_metadata = sys.argv[4]
    update_comments(source_file, source_directory, source_metadata)




'''
how it works:
1) python3 mp3operations.py read ~/Music/songsyt0822_1/ ~/Music/
       reads the metadata from the files and generates a csv file with the following format
       /mp3_metadata.csv"
    output format:
    path@album@artist@title@@
    /home/jose/Music/songsyt0822_1/Amazing Official Music/None/Aerosmith_-_Amazing_Official_Music_Video-zSmOvYzSeaQ.mp3@Get a Grip@Aerosmith@Amazing@@

    or 
    'read_commas'
    python3 mp3operations.py read_commas ~/music_org/organized_final/final ~/music_org/organized_final/new/

       reads the metadata from the files and generates a csv file with the following format
       /mp3_metadata.csv"
    output format:
    path,album,artist,title,,
    /home/jose/Music/songsyt0822_1/Amazing Official Music/None/Aerosmith_-_Amazing_Official_Music_Video-zSmOvYzSeaQ.mp3,Get a Grip,Aerosmith,Amazing,,

2) with the generated  /mp3_metadata.csv", run the cypress application that trys to get the album name from google
     cp ~/Music/mp3_metadata.csv ~/Cypress/cypress/fixtures/mp3_metadata.csv
     run the cypress app:
     -- OLD cypress:* npx cypress run --headless  --spec cypress/e2e/2-advanced-examples/music_parse.cy.js
     jose@jose-OptiPlex-7050:~/Development$ npx cypress run --headless  --spec cypress/e2e/music_parse.cy.js 
     the output file is generated under fixtures/outputdata.csv
     

     or the new getting it from mp3 

     ELECTRON_ENABLE_LOGGING=1 npx cypress run --spec "cypress/e2e/music_parse_yt.cy.js"



3)python3 ~/Development/python/mp3operations.py consolidate_album_info ~/Music/mp3_metadata.csv ~/Development/cypress/fixtures/outputdata.csv

will update the mp3_metadata.csv with the album information
will produce ~/Music/to_reprocess.csv

cp ~/Music/to_reprocess.csv ~/Development/cypress/fixtures/mp3_metadata.csv

go to step2 to reprocess files

if all files processed go to step4 to update the file metadata




-------   IMPORTANT: make sure all rows of the mp3_metadata file have the curated column set to TRUE
all final stages combined
python3 ~/Development/python/mp3operations.py final_stages ~/music_org/temp/organized/ ~/music_org/temp/mp3_metadata.csv ~/music_org/temp/inter/ ~/music_org/temp/final

--------  OR  step by step-------

4) writer, complete
python3 ~/Development/python/mp3operations.py update_metadata ~/music_org/temp/songsyt_0124 ~/music_org/temp/mp3_metadata.csv


4new) writer, update comments
python3 mp3operations.py update_comments ~/music_org/organized_final/final ~/music_org/organized_final/new/mp3_metadata.csv ~/music_org/organized_final/new/metadata.csv


5)organize files
python3 mp3operations.py move_files_v1 ~/music_org/organized_final/final/ ~/music_org/organized_final/new

param2: source dir
param3: dest dir "it will also create music_og, under the dest


-------  Step 6 is not reliable, messes up data.
----> continue here see if it makes sense, it does make sense to apply at the end
precondition: run python3 mp3operations.py read_commas ~/Music/songsyt0822_1/ ~/Music/
python3 ~/Development/python/mp3operations.py read_commas ~/music_org/temp/organized/music_org/ ~/music_org/temp/organized/

6)is the one that consolidates songs under the same artist (and similar)
python3 ~/Development/python/mp3operations.py move_files ~/music_org/temp/t2/mp3_metadata.csv ~/music_org/temp/t2/final/ 
    ##Sys.argv[2] = source filename containing final list of songs to consolidate
    ##Sys.argv[3] = destination path

-----
combined steps 4,5, pre6 and 6 here:
    source_directory = sys.argv[2]
    source_file = sys.argv[3]
    destination_directory = sys.argv[4]
    final_directory = sys.argv[5]
example: 
python3 ~/Development/python/mp3operations.py final_stages ~/music_org/temp/songsyt_0424/ ~/music_org/temp/mp3_metadata.csv ~/music_org/temp/organized/ ~/music_org/temp/final2/


'''
################################################
