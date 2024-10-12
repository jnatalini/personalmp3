import os
import librosa
import pandas as pd
from mutagen.easyid3 import EasyID3
import pdb
import eyed3

from openai import OpenAI
client = OpenAI()



# Directory containing mp3 files
#find . -iname "*.mp3" -exec mv {} . \;
audio_dir = '/home/jose/Music/'

# Initialize an empty list to hold our data
data = []

for file in os.listdir(audio_dir):
    try:
        print(file)
        if file.endswith('.mp3'):
            filepath = os.path.join(audio_dir, file)
            print(filepath)
            
            # Extract Metadata
            metadata = EasyID3(filepath)
            title = metadata.get('title', ['Unknown'])[0]
            artist = metadata.get('artist', ['Unknown'])[0]
            genre = metadata.get('genre', ['Unknown'])[0]
            
            # Extract Audio Features
            y, sr = librosa.load(filepath)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            chroma_stft = librosa.feature.chroma_stft(y=y, sr=sr).mean()
            spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr).mean()
            
            # Append to data
            data.append([title, artist, genre, tempo, chroma_stft, spectral_contrast,filepath])
    except Exception as e:
        print(e)

# Create DataFrame
columns = ['Title', 'Artist', 'Genre', 'Tempo', 'Chroma_Stft', 'Spectral_Contrast','File Path']
df = pd.DataFrame(data, columns=columns)
#pdb.set_trace()
print(df.head())

# Handle missing values (if any)
df.fillna('Unknown', inplace=True)

# Normalize feature values for machine learning
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
df[['Tempo', 'Chroma_Stft', 'Spectral_Contrast']] = scaler.fit_transform(df[['Tempo', 'Chroma_Stft', 'Spectral_Contrast']])

print(df)

#pdb.set_trace()
from sklearn.cluster import KMeans

# Define the number of clusters
try:
    cluster_size = df['Artist'].nunique()
    kmeans = KMeans(n_clusters=cluster_size, max_iter=1000, init='k-means++')
    df['Cluster'] = kmeans.fit_predict(df[['Tempo', 'Chroma_Stft', 'Spectral_Contrast']])
except Exception as e:
    print(e)
'''
from sklearn.decomposition import PCA

pca = PCA(n_components=2)
components = pca.fit_transform(df[['Tempo', 'Chroma_Stft', 'Spectral_Contrast']])
df['PCA1'] = components[:, 0]
df['PCA2'] = components[:, 1]

kmeans = KMeans(n_clusters=5)
df['Cluster'] = kmeans.fit_predict(df[['PCA1', 'PCA2']])
'''

'''
from sklearn.cluster import AgglomerativeClustering

agglomerative = AgglomerativeClustering(n_clusters=5)
df['Cluster'] = agglomerative.fit_predict(df[['Tempo', 'Chroma_Stft', 'Spectral_Contrast']])
'''



# Group and organize songs by clusters

organized_data = df.sort_values(by='Cluster')
print(organized_data[['Title', 'Artist', 'Cluster']])
'''
import shutil

for _, row in organized_data.iterrows():
    try:
        cluster_folder = f"cluster_{row['Cluster']}"
        if not os.path.exists(audio_dir + '/' + cluster_folder):
            os.makedirs(audio_dir + '/' + cluster_folder)
        #pdb.set_trace()
        #shutil.move(os.path.join(audio_dir, row['Title'] + '.mp3'), cluster_folder)
        shutil.move(row['File Path'], audio_dir + '/' + cluster_folder)
    except Exception as e:
        print(row)
        print(e)

'''

def get_info(row):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"this is a song name: {row['Title']}. This is possibly the artist  of the song: {row['Artist']}, but it may not be accurate. Based on this information, find the artist, album and song title. Provide the response in json format, with fields 'Artist', 'Album' and 'Title'. If you cannot find it return None for each field. Only include the json response, without any additional text."
            }
        ]
    )
    return completion.choices[0].message.content


def update_metadata(filenamepath, metadata):
    audio = eyed3.load(filenamepath)
    audio.tag.album = metadata['Album']
    audio.tag.artist = metadata['Artist']
    audio.tag.album_artist = metadata['Artist']
    audio.tag.title = metadata['Title']
    audio.tag.save()



import json

for _, row in organized_data.iterrows():
    try:
        response = get_info(row)
        json_response = json.loads(response[8:].replace('\n', ' ').replace('```',''))
        print(json_response)
        update_metadata(row['File Path'], json_response)

    except Exception as e:
        print(row)
        print(response)
        print(e)



