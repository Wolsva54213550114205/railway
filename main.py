from flask import Flask, request, jsonify
from openai import OpenAI
import time
from langdetect import detect
import random
import string
import requests
import os
from pytube import YouTube
from pyshorteners import Shortener
import isodate
import re
from datetime import datetime
import pytz
import pycountry
import io
app = Flask(__name__)

RESOLUTIONS_DICT = {'144p': 144, '240p': 240, '360p': 360, '480p': 480, '720p': 720, '1080p': 1080, '1440p': 1440, '2160p': 2160}

def generate_random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_closest_resolution(resolution_choice, available_resolutions):
    """
    Cette fonction prend en entrée la résolution choisie et la liste des résolutions disponibles
    Elle renvoie la résolution la plus proche disponible dans la liste.
    """
    # Extraire la partie numérique de la résolution choisie
    chosen_resolution_numeric = int(resolution_choice[:-1])

    # Convertir les résolutions disponibles en parties numériques pour calculer la différence
    available_resolutions_numeric = [int(res[:-1]) for res in available_resolutions]

    # Trouver la résolution la plus proche
    closest_resolution_numeric = min(available_resolutions_numeric, key=lambda x: abs(x - chosen_resolution_numeric))

    # Récupérer la résolution la plus proche
    closest_resolution = [res for res in available_resolutions if int(res[:-1]) == closest_resolution_numeric][0]

    return closest_resolution

# Initialisation de l'API OpenAI
openai_client = OpenAI(base_url='https://api.naga.ac/v1', api_key='ng-nqFIdKdQmQvQyb3y56eWfTZWyzFsC')

@app.route('/exemple')
def exemple():
    data = {"exemple": "Ceci est un exemple"}
    return jsonify(data)

@app.route('/gpt3.5', methods=['GET'])
def gpt3_5_endpoint():
    # Récupérer le message depuis l'URL
    message = request.args.get('message', '')

    # Vérifier si le message est vide
    if not message:
        return jsonify({'error': 'Veuillez entrer un message'})

    # Enregistrer le temps de début de la requête
    start_time = time.time()

    # Utiliser le message pour interagir avec l'API OpenAI
    response = openai_client.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[{'role': 'user', 'content': message}]
    )

    # Calculer le temps de réponse
    end_time = time.time()
    response_time = end_time - start_time

    # Formater le temps de réponse pour l'afficher de manière conviviale
    response_time_formatted = "{:.1f}s".format(response_time)

    # Extraire la réponse de l'API OpenAI
    answer = response.choices[0].message.content

    # Ajouter d'autres informations
    prompt_length = len(message)
    response_length = len(answer)
    
    # Déterminer la langue de la réponse
    response_language = detect(answer)

    # Créer une réponse JSON avec toutes les informations
    json_response = {
        'message': message,
        'response': answer,
        'response_time': response_time_formatted,
        'prompt_length': prompt_length,
        'response_length': response_length,
        'language': response_language
    }

    # Retourner la réponse JSON
    return jsonify(json_response)

@app.route('/nitro', methods=['GET'])
def generate_random_strings():
    range_value = request.args.get('x', default='1')  # Récupérer la valeur de 'x' de l'URL, par défaut 1
    try:
        range_value = int(range_value)
        if range_value > 10000:
            return jsonify({"error": "Le maximum est 10000"}), 400  # Renvoyer une erreur 400 si la valeur est supérieure à 10000
    except ValueError:
        range_value = 1
    
    random_strings = ["https://discord.gift/" + generate_random_string(16) for _ in range(range_value)]
    return jsonify(random_strings)
    
@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "Cette page n'existe pas", "discord": "dsc.gg/octopia"}), 404

@app.route('/youtube-dl', methods=['GET'])
def download_video():
    url = request.args.get('url')
    resolution_choice = request.args.get('res')

    # Créer une instance de la classe YouTube
    yt = YouTube(url)

    # Afficher les différentes résolutions disponibles
    available_resolutions = [stream.resolution for stream in yt.streams if stream.resolution]
    print("Résolutions disponibles :", available_resolutions)

    # Vérifier si la résolution spécifiée contient 'p', sinon, l'ajouter
    if 'p' not in resolution_choice:
        resolution_choice += 'p'

    # Si la résolution spécifiée n'est pas dans le dictionnaire, trouver la plus proche
    if resolution_choice not in RESOLUTIONS_DICT:
        resolution_choice = get_closest_resolution(resolution_choice, list(RESOLUTIONS_DICT.keys()))

    # Sélectionner la vidéo avec la résolution spécifiée
    video_stream = yt.streams.filter(res=resolution_choice).first()

    # Obtenir l'URL de la vidéo
    video_url = video_stream.url if video_stream else None

    # Raccourcir le lien avec TinyURL
    if video_url:
        shortener = Shortener()
        short_url = shortener.tinyurl.short(video_url)
        return jsonify({"short_url": short_url, "url": video_url})
    else:
        return jsonify({"error": "Aucun flux vidéo trouvé."})

@app.route('/youtube-info', methods=['GET'])
def youtube_video_info():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is missing'}), 400

    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    video_info = get_video_info(video_id)
    return jsonify(video_info)

def extract_video_id(url):
    video_id = None
    patterns = [
        r'(?:(?:https?:)?\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break
    return video_id

def get_video_info(video_id):
    api_key = 'AIzaSyDiv_bvX2QLBHawch-EKyeDlItomOogfHQ'  # Replace with your YouTube Data API key
    url = f'https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={api_key}&part=snippet,contentDetails,statistics'
    response = requests.get(url)
    data = response.json()

    video_info = {}
    if 'items' in data and len(data['items']) > 0:
        item = data['items'][0]
        snippet = item['snippet']
        content_details = item['contentDetails']
        statistics = item['statistics']

        video_info['title'] = snippet.get('title', '')
        video_info['description'] = snippet.get('description', '')
        
        # Formatting duration
        duration_dict = format_duration(content_details.get('duration', ''))  # Convertir en format lisible
        video_info['duration'] = duration_dict
        video_info['view_count'] = statistics.get('viewCount', '')
        video_info['comment_count'] = statistics.get('commentCount', '')
        video_info['like_count'] = statistics.get('likeCount', '')
        video_info['video_link'] = f'https://www.youtube.com/watch?v={video_id}'
        video_info['video_id'] = video_id
        video_info['thumbnail_link'] = snippet['thumbnails']['default']['url']
        video_info['channel_title'] = snippet.get('channelTitle', '')
        video_info['channel_name'] = snippet.get('channelTitle', '')
        video_info['channel_id'] = snippet.get('channelId', '')
        
        # Récupérer l'image du profil de la chaîne
        channel_id = snippet.get('channelId', '')
        channel_image = get_channel_image(api_key, channel_id)
        video_info['channel_image'] = channel_image
    
    return video_info

def format_duration(duration_iso):
    duration_seconds = isodate.parse_duration(duration_iso).total_seconds()
    hours = int(duration_seconds // 3600)
    minutes = int((duration_seconds % 3600) // 60)
    seconds = int(duration_seconds % 60)
    return {'hours': hours, 'minutes': minutes, 'seconds': seconds}

def get_channel_image(api_key, channel_id):
    url = f'https://www.googleapis.com/youtube/v3/channels?key={api_key}&id={channel_id}&part=snippet'
    response = requests.get(url)
    data = response.json()
    
    if 'items' in data and len(data['items']) > 0:
        return data['items'][0]['snippet']['thumbnails']['default']['url']
    else:
        return ''

CLIENT_ID = "029dde2623291bf"

def generate_qr_image(url):
    try:
        api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url}"
        response = requests.get(api_url)
        if response.status_code == 200:
            return response.content
        else:
            return None
    except Exception as e:
        print("Erreur lors de la génération du code QR :", e)
        return None

@app.route('/qr')
def generate_qr_code():
    url = request.args.get('url')

    if not url:
        return jsonify({'error': 'Paramètre URL manquant'}), 400

    # Vérifier si l'URL se termine par "/text"
    if url.endswith("/text"):
        url = url[:-5]
        shortener = Shortener()
        short_url = shortener.tinyurl.short(f"https://api-octopia.vercel.app/qr?url={url}")
        return jsonify({"short_url": short_url})

    else:
        # Générer le QR code en utilisant la fonction generate_qr_image
        qr_img = generate_qr_image(url)

        if qr_img is None:
            return jsonify({'error': 'Impossible de générer le code QR'}), 500

        # Retourner l'image du QR code
        return qr_img, 200, {'Content-Type': 'image/png'}

def get_month_name(month_number):
    months_fr = [
        "janvier", "fevrier", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "decembre"
    ]
    return months_fr[month_number - 1] if 1 <= month_number <= 12 else None

def country_to_timezone(country):
    # Vérifie si le pays est un nom de pays valide
    try:
        country_info = pycountry.countries.lookup(country)
        country_code = country_info.alpha_2.lower()
    except LookupError:
        # Si le pays n'est pas un nom de pays valide, vérifie s'il s'agit d'un code de pays valide
        try:
            pycountry.countries.lookup(country.upper())
            country_code = country.lower()
        except LookupError:
            return None

    # Obtient le code de pays à partir du nom de pays ou du code de pays
    return pytz.country_timezones.get(country_code, None)

@app.route('/time', methods=['GET'])
def get_time():
    country = request.args.get('country')

    if country is None:
        return jsonify({'error': 'Le parametre "country" est requis'}), 400

    timezone = country_to_timezone(country)

    if timezone is None:
        return jsonify({'error': 'Pays non trouve dans la liste des fuseaux horaires'}), 400

    current_datetime = datetime.now(pytz.timezone(timezone[0]))

    # Date
    date_fr = "{} {} {}".format(
        current_datetime.strftime('%d'),
        get_month_name(current_datetime.month),
        current_datetime.strftime('%Y')
    )
    date_info = {
        'day': current_datetime.strftime('%d'),
        'month': current_datetime.strftime('%m'),
        'year': current_datetime.strftime('%Y'),
        'date_fr': date_fr
    }

    # Heure
    time_info = {
        'hour': current_datetime.strftime('%H'),
        'minute': current_datetime.strftime('%M'),
        'second': current_datetime.strftime('%S'),
        'time': current_datetime.strftime('%H:%M:%S')
    }

    # Conversion en JSON avec ensure_ascii=False pour conserver les caractères Unicode non ASCII
    return jsonify({'country': country, 'date': date_info, 'time': time_info}), 200, {'Content-Type': 'application/json; charset=utf-8'}




@app.route('/ping')
def ping():
    start_time = time.time()
    latency = time.time() - start_time
    # Convert to milliseconds and round to 1 decimal place
    latency_ms = round(latency * 1000, 1)
    return jsonify({"message": "pong", "latency": f"{latency_ms}ms"})







        
if __name__ == '__main__':
    app.run(debug=True)
