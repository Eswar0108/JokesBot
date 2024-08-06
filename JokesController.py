import tweepy
import time
import requests

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

# JokeAPI endpoint
JOKE_API_URL = 'https://v2.jokeapi.dev/joke/Any'

def get_joke():
    response = requests.get(JOKE_API_URL)
    data = response.json()
    if data['type'] == 'single':
        return data['joke']
    else:
        return f"{data['setup']} - {data['delivery']}"

# Function to create tweepy client and API for each account
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
        auth = tweepy.OAuth1UserHandler(
            account['api_key'], account['api_secret'],
            account['access_token'], account['access_token_secret']
        )
        api = tweepy.API(auth)
        clients.append((client, api, account))
    return clients

# Function to post a tweet
def create_tweet(client, account, text):
    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data['id']
        print(f"Tweeted: {text}")
        print(f"Channel: {account['channel_name']} | Email: {account['email']}")
        print(f"Tweet ID: {tweet_id}")
        return tweet_id
    except tweepy.TweepyException as e:
        error_message = str(e)
        if '429' in error_message:
            # Extract rate limit reset time and wait until then
            reset_time = int(e.response.headers.get('x-rate-limit-reset', time.time() + 60))
            wait_time = reset_time - time.time()
            print(f"Rate limit exceeded, waiting to retry in {wait_time} seconds...")
            time.sleep(max(wait_time, 0))  # Wait until rate limit resets
        elif 'Duplicate content' in error_message or '403 Forbidden' in error_message:
            # Duplicate content error or general forbidden error
            print(f"Duplicate content detected or forbidden error, skipping tweet: {text}")
        else:
            print(f"Error: {e}")
        return None

# Function to check rate limit status for tweet creation
def get_rate_limit_status(api):
    try:
        rate_limit_status = api.rate_limit_status(resources='statuses')
        limit_data = rate_limit_status['resources']['statuses']['/statuses/update']
        return limit_data
    except tweepy.TweepyException as e:
        print(f"Error checking rate limit: {e}")
        return None

# Function to post multiple tweets with rate limit handling
def post_tweets(clients, tweets):
    for tweet in tweets:
        for client, api, account in clients:
            limit_data = get_rate_limit_status(api)
            if limit_data and limit_data['remaining'] > 0:
                create_tweet(client, account, tweet)
                print("Waiting 10 seconds before posting the next tweet...")
                time.sleep(10)  # Wait to ensure posting no more than 5 tweets per minute
            else:
                reset_time = limit_data['reset'] if limit_data else time.time() + 60
                wait_time = reset_time - time.time()
                print(f"Rate limit reached. Waiting for {wait_time} seconds before retrying...")
                time.sleep(max(wait_time, 0))

# Create clients for each account
clients = create_clients(accounts)

# List of tweets to post
tweets = [get_joke() for _ in range(5)]  # Fetch 5 jokes

# Post the tweets
post_tweets(clients, tweets)

print("Completed")
