import nltk
from textblob import TextBlob

# Download necessary NLTK corpora
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('brown')

# Rest of your imports and code...
import tweepy
import time
import requests
import random
from datetime import datetime, timedelta
from requests.exceptions import ConnectionError
import pyjokes
from PIL import Image, ImageDraw, ImageFont
import io
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# List of credentials for each account
accounts = [
    {
        'api_key': 'lHfKp2CUZI5p1NT8R1NtS4IS3',
        'api_secret': 'Zwfp6di94AkIQevsM02jk7cFV3r7B7YtvT5tAlCNMwmzGtd46s',
        'bearer_token': 'AAAAAAAAAAAAAAAAAAAAAMh5tQEAAAAA0XUYm6dvR86wYxZVeZnvJwifcmk%3DpIVfhzA0kiyFHqMnClRNA5yJeTI7gOKKUjQssPDKT0dHBjloZ2',
        'access_token': '1619340338367463424-5869kAWxO7evDDT8ecm3BwjU2fHvAD',
        'access_token_secret': 'ymA0aDfJXtTMj7HEiJFA1Qe0tDrIPVOz7U96zPHg9eKtz',
        'email': 'ultimatum@yopmail.com',
        'channel_name': 'Ultimatum - Maket Maven'
    }
]

MAX_TWEETS_PER_DAY = 500
TWEETS_PER_ACCOUNT_PER_DAY = MAX_TWEETS_PER_DAY // len(accounts)

tweet_count = {account['email']: 0 for account in accounts}
reset_time = {account['email']: datetime.now() + timedelta(days=1) for account in accounts}

MAX_TWEET_LENGTH = 280

def get_joke_from_jokeapi():
    JOKE_API_URL = 'https://v2.jokeapi.dev/joke/Any?format=txt&safe-mode'
    try:
        response = requests.get(JOKE_API_URL)
        joke = response.text.strip()
        if len(joke) > MAX_TWEET_LENGTH:
            return None
        return joke
    except ConnectionError:
        logging.error("Failed to connect to JokeAPI")
        return None

def get_joke_from_pyjokes():
    try:
        joke = pyjokes.get_joke()
        if len(joke) > MAX_TWEET_LENGTH:
            return None
        return joke
    except Exception as e:
        logging.error(f"Failed to get joke from pyjokes: {e}")
        return None

def get_joke_from_official_joke_api():
    JOKE_API_URL = 'https://official-joke-api.appspot.com/random_joke'
    try:
        response = requests.get(JOKE_API_URL)
        data = response.json()
        joke = f"{data['setup']} - {data['punchline']}"
        if len(joke) > MAX_TWEET_LENGTH:
            return None
        return joke
    except ConnectionError:
        logging.error("Failed to connect to Official Joke API")
        return None

def get_joke(round_robin_counter):
    fetchers = [get_joke_from_jokeapi, get_joke_from_pyjokes, get_joke_from_official_joke_api]
    joke = fetchers[round_robin_counter % len(fetchers)]()
    
    if joke:
        sentiment = TextBlob(joke).sentiment
        keywords = [word for word in TextBlob(joke).noun_phrases if word.lower() not in nltk.corpus.stopwords.words('english')]
        
        if sentiment.polarity > 0.5:
            emojis = ["😂", "🤣", "😆"]
        elif sentiment.polarity < -0.5:
            emojis = ["😞", "😢", "😟"]
        else:
            emojis = ["😅", "🙂", "😐"]

        hashtags = [f"#{keyword.replace(' ', '')}" for keyword in keywords]
        
        joke_with_emojis = f"{joke} {' '.join(emojis)}"
        joke_with_emojis_and_hashtags = f"{joke_with_emojis} {' '.join(hashtags)}"
        
        if len(joke_with_emojis_and_hashtags) <= MAX_TWEET_LENGTH:
            return joke_with_emojis_and_hashtags
        elif len(joke_with_emojis) <= MAX_TWEET_LENGTH:
            return joke_with_emojis
        else:
            return joke
    return None

def create_joke_image(joke_text):
    image = Image.new('RGB', (800, 400), color='white')
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()

    text_width, text_height = draw.textsize(joke_text, font=font)
    text_x = (800 - text_width) / 2
    text_y = (400 - text_height) / 2
    draw.text((text_x, text_y), joke_text, fill='black', font=font)
    
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer

def create_clients(accounts):
    clients = []
    for account in accounts:
        client = tweepy.Client(
            bearer_token=account['bearer_token'],
            consumer_key=account['api_key'],
            consumer_secret=account['api_secret'],
            access_token=account['access_token'],
            access_token_secret=account['access_token_secret']
        )
        clients.append((client, account))
    return clients

def can_tweet(account_email):
    now = datetime.now()
    if now >= reset_time[account_email]:
        tweet_count[account_email] = 0
        reset_time[account_email] = now + timedelta(days=1)
    return tweet_count[account_email] < TWEETS_PER_ACCOUNT_PER_DAY

def is_tweet_length_valid(text):
    return len(text) <= MAX_TWEET_LENGTH

def create_tweet(client, account, text, media=None):
    if not can_tweet(account['email']):
        logging.info(f"Daily limit reached for account: {account['channel_name']}. Waiting for reset.")
        return None

    if not is_tweet_length_valid(text):
        logging.info(f"Tweet text is too long: {text}")
        return None

    retries = 5
    delay = 10
    while retries > 0:
        try:
            if media:
                media_id = client.upload_media(media)
                response = client.create_tweet(text=text, media_ids=[media_id])
            else:
                response = client.create_tweet(text=text)
                
            tweet_id = response.data['id']
            tweet_count[account['email']] += 1
            logging.info(f"Tweeted: {text}")
            logging.info(f"Channel: {account['channel_name']} | Email: {account['email']}")
            logging.info(f"Tweet ID: {tweet_id}")
            return tweet_id
        except tweepy.TooManyRequests as e:
            logging.error(f"Rate limit exceeded. Error: {e}")
            time.sleep(15 * 60)
            return None
        except (tweepy.TweepyException, ConnectionError) as e:
            error_message = str(e)
            if 'Duplicate content' in error_message or '403 Forbidden' in error_message:
                logging.warning(f"Duplicate content detected or forbidden error, skipping tweet: {text}")
                return None
            elif '400 Bad Request' in error_message:
                logging.error(f"Bad request error: {error_message}")
                return None
            else:
                logging.error(f"Error: {e}")
                retries -= 1
                logging.info(f"Retrying in {delay} seconds... ({5 - retries} retries left)")
                time.sleep(delay)
                delay *= 2

    logging.error("Failed to post tweet after several retries.")
    return None

def post_tweets(clients, tweets):
    for tweet in tweets:
        for client, account in clients:
            if can_tweet(account['email']):
                media = create_joke_image(tweet)
                create_tweet(client, account, tweet, media=media)
                logging.info("Waiting 10 seconds before posting the next tweet...")
                time.sleep(10)
            else:
                logging.info(f"Cannot tweet for account: {account['channel_name']} due to daily limit.")
        logging.info("Waiting 1 minute before checking limits again...")
        time.sleep(60)

if __name__ == "__main__":
    clients = create_clients(accounts)
    
    round_robin_counter = 0
    while True:
        joke = get_joke(round_robin_counter)
        round_robin_counter += 1
        if joke:
            post_tweets(clients, [joke])
        logging.info(f"Joke processed: {joke}")
        time.sleep(3600)  # Wait an hour before the next iteration
