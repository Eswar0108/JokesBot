import tweepy
import time
import requests
from datetime import datetime, timedelta
from requests.exceptions import ConnectionError

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

# Track tweet counts and reset times
tweet_count = {account['email']: 0 for account in accounts}
reset_time = {account['email']: datetime.now() + timedelta(days=1) for account in accounts}

# Twitter's maximum character limit for a tweet
MAX_TWEET_LENGTH = 280

# Function to fetch jokes from JokeAPI (safe mode)
def get_joke_from_jokeapi():
    JOKE_API_URL = 'https://v2.jokeapi.dev/joke/Any?format=txt&safe-mode'
    try:
        response = requests.get(JOKE_API_URL)
        joke = response.text.strip()
        if len(joke) > MAX_TWEET_LENGTH:
            return None
        return joke
    except ConnectionError:
        print("Failed to connect to JokeAPI")
        return None

# Function to fetch jokes from pyjokes
def get_joke_from_pyjokes():
    import pyjokes
    try:
        joke = pyjokes.get_joke()
        if len(joke) > MAX_TWEET_LENGTH:
            return None
        return joke
    except Exception as e:
        print(f"Failed to get joke from pyjokes: {e}")
        return None

# Function to fetch jokes from Official Joke API
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
        print("Failed to connect to Official Joke API")
        return None

# Round-robin fetching of jokes
def get_joke(round_robin_counter):
    fetchers = [get_joke_from_jokeapi, get_joke_from_pyjokes, get_joke_from_official_joke_api]
    return fetchers[round_robin_counter % len(fetchers)]()

# Function to create tweepy client for each account
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

# Function to check if we can still tweet
def can_tweet(account_email):
    now = datetime.now()
    if now >= reset_time[account_email]:
        tweet_count[account_email] = 0
        reset_time[account_email] = now + timedelta(days=1)
    return tweet_count[account_email] < TWEETS_PER_ACCOUNT_PER_DAY

# Function to validate tweet length
def is_tweet_length_valid(text):
    return len(text) <= MAX_TWEET_LENGTH

# Function to post a tweet with retry mechanism
def create_tweet(client, account, text):
    if not can_tweet(account['email']):
        print(f"Daily limit reached for account: {account['channel_name']}. Waiting for reset.")
        return None

    if not is_tweet_length_valid(text):
        print(f"Tweet text is too long: {text}")
        return None

    retries = 5
    delay = 10
    while retries > 0:
        try:
            response = client.create_tweet(text=text)
            tweet_id = response.data['id']
            tweet_count[account['email']] += 1
            print(f"Tweeted: {text}")
            print(f"Channel: {account['channel_name']} | Email: {account['email']}")
            print(f"Tweet ID: {tweet_id}")
            return tweet_id
        except tweepy.TooManyRequests as e:
            print(f"Rate limit exceeded. Error: {e}")
            time.sleep(15 * 60)  # Wait 15 minutes as a safe measure
            return None
        except (tweepy.TweepyException, ConnectionError) as e:
            error_message = str(e)
            if 'Duplicate content' in error_message or '403 Forbidden' in error_message:
                print(f"Duplicate content detected or forbidden error, skipping tweet: {text}")
                return None
            elif '400 Bad Request' in error_message:
                print(f"Bad request error: {error_message}")
                return None
            else:
                print(f"Error: {e}")
                retries -= 1
                print(f"Retrying in {delay} seconds... ({5 - retries} retries left)")
                time.sleep(delay)
                delay *= 2  # Exponential backoff

    print("Failed to post tweet after several retries.")
    return None

# Function to post multiple tweets with rate limit handling
def post_tweets(clients, tweets):
    for tweet in tweets:
        for client, account in clients:
            if can_tweet(account['email']):
                create_tweet(client, account, tweet)
                print("Waiting 10 seconds before posting the next tweet...")
                time.sleep(10)  # Wait to ensure posting no more than 5 tweets per minute
            else:
                print(f"Cannot tweet for account: {account['channel_name']} due to daily limit.")
        print("Waiting 1 minute before checking limits again...")
        time.sleep(60)  # Wait a bit before the next check

# Create clients for each account
clients = create_clients(accounts)

# Fetch jokes and post the tweets
round_robin_counter = 0
while True:
    joke = get_joke(round_robin_counter)
    round_robin_counter += 1
    if joke:
        post_tweets(clients, [joke])
    print("joke, Completed", joke)

print("Completed")
