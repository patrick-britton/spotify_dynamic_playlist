import sys
import os
import time
from datetime import datetime, timedelta
import pandas as pd
import pytz
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from difflib import SequenceMatcher
import numpy as np
import re

def print_break():
    print('__________________________________________________')

def initialize_file_location(filepath):
    # Tests for the existence and validity of a filepath, creating it if it does not exist.
    if not filepath:
        print('No filepath specified.')
        print('Please check the script header for updates.')
        return False
    elif not os.path.exists(filepath):
        print(filepath, 'does not exist.')
        os.makedirs(filepath)
        print(filepath, 'has now been created.')
        return True
    elif not os.path.isdir(filepath):
        print(filepath, 'exists, but is not a directory.')
        return False
    else:
        # Directory already exists and is a valid directory
        return True

def local_storage_init(filepath):
    # Dynamic playlist requires 2 pre-requisite files exist, even if they're blank.
    # 1. A rankings file where the user can add or edit the "star" rankings for their songs.
    # 2. A file that has the complete listening history that will be amended over time.

    # Test for and create the rankings file if it does not exist:
    try:
        rankings = os.path.join(filepath, 'rankings.csv')
        if not os.path.exists(rankings):
            column_list = ['track_id', 'track_name', 'artist_name', 'duration_ms', 'star_rating']
            df = pd.DataFrame(columns=column_list)
            df.to_csv(rankings, index=False)
            print('Rankings file initialized.')

        # Test for and create the listening history file if it does not exist:
        listen_history = os.path.join(filepath, 'listen_history.csv')
        if not os.path.exists(listen_history):
            column_list = ['track_name', 'artist_name', 'album_name', 'played_at', 'played_at_timestamp', 'duration_ms',
                           'track_id', 'popularity', 'meta_batch', 'is_running_song']
            df = pd.DataFrame(columns=column_list)
            df.to_csv(listen_history, index=False)
            print('Listening history file initialized.')

        # Test for and create the playlist removals file if it does not exist.
        playlist_removals = os.path.join(filepath, 'playlist_removals.csv')
        if not os.path.exists(playlist_removals):
            column_list = ['track_id',
                           'track_name',
                           'track_popularity',
                           'track_duration_ms',
                           'artist_name',
                           'artist_id',
                           'album_name',
                           'album_id',
                           'duration_ms',
                           'stars',
                           'last_played',
                           '5_star_recent_plays',
                           '4_star_recent_plays',
                           '3_star_recent_plays',
                           '2_star_recent_plays',
                           '1_star_recent_plays',
                           'star_plays',
                           'ranking']
            df = pd.DataFrame(columns=column_list)
            df.to_csv(playlist_removals, index=False)
            print('Playlist removal file initialized.')
    except Exception as e:
        print('Error validating local files: ', e)
        print('Script terminating.')
        sys.exit(1)

def local_initialization_check(cred_loc, stor_loc):
    # Tests to see if user inputs from the execution script are valid.
    if not initialize_file_location(cred_loc):
        print('Spotify credential location not initialized, stopping script.')
        sys.exit(1)
    if not initialize_file_location(stor_loc):
        print('Spotify credential location not initialized, stopping script.')
        sys.exit(1)
    else:
        local_storage_init(stor_loc)
        print('File structure verified.')

def clear_local_file(filepath, service, file_type, file_class):
    # Deletes a credential file, if it exists.
    filename = service + '_' + file_type + '.txt'
    filename = os.path.join(filepath, file_type)

    # Read the information if it exists.
    if os.path.exists(filename):
        os.remove(filename)
        print(service, file_type, file_class, 'file deleted.')

def read_login(cred_path, service, login_type):
    # Either loads the client ID from local storage or accepts user input.
    cred_file = service + '_' + login_type + '.txt'
    cred_file = os.path.join(cred_path, cred_file)
    result = None

    # Read the information if it exists.
    if os.path.exists(cred_file):
        with open(cred_file, 'r') as f:
            result = f.read().strip()

    # Ask for the information if it does not.
    if not result:
        print('Please input your', login_type, 'for', service)
        result = input('Input --> ')
        # Save the input locally
        with open(cred_file, 'w') as f:
            f.write(result)
    return result

def attempt_login(cred_path):
    # Checks for local credentials or asks the user to enter them, and then save them locally.

    # Read in the appropriate credentials
    client_id = read_login(cred_path, 'Spotify', 'Client ID')
    client_secret = read_login(cred_path, 'Spotify', 'Client Secret')
    redirect_uri = read_login(cred_path, 'Spotify', 'Redirect URI')

    # Declare the scope
    scope_list = ['user-read-recently-played',
                  'playlist-read-private',
                  'playlist-read-collaborative',
                  'playlist-modify-private',
                  'playlist-modify-public']
    scope = ''
    for scope_type in scope_list:
        scope = scope + scope_type + ' '
    scope = scope.strip()

    # Attempt to login once.
    try:
        auth_manager = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri,
                                    scope=scope, cache_path = os.path.join(cred_path, '.spotify_cache'))
        spotify = spotipy.Spotify(auth_manager=auth_manager)
        current_user = spotify.current_user()
        print('Successfully logged into Spotify as', current_user['display_name'])
        return spotify
    except Exception as e:
        print('Failed to login:', e)
        return None

def spotify_login(cred_path):
    # Attempts to log into Spotify, using stored credentials if available.
    # If initial login fails, will clear any saved credentials and try additional times.

    #Attempt #1
    client = attempt_login(cred_path)
    total_attempts = 3
    remaining_attempts = total_attempts -1

    # If attempt failed, try again a few times:
    while client is None and remaining_attempts > 0:
        print('Login failed.')
        remaining_attempts = remaining_attempts -1
        clear_local_file(cred_path, 'spotify', 'client_id', 'credential')
        clear_local_file(cred_path, 'spotify', 'client_secret', 'credential')
        print('Attempt #', total_attempts - remaining_attempts, 'of', total_attempts)
        client = attempt_login(cred_path)

    # If login does not succeed, terminate the script and start over.
    if client is None:
        print('Unable to login after', total_attempts, 'attempts.')
        print('You may need to configure the Spotify App first.')
        print('See https://developer.spotify.com/ for more information.')
        print('Terminating Script')
        sys.exit(1)
    else:
        return client

def get_playlist_id(storage_loc, playlist_type):
    # Loads or requests from the user the playlist id corresponding to the specific type.
    id_file = playlist_type + '.txt'
    id_file = os.path.join(storage_loc, id_file)
    result = None

    # Read the information if it exists.
    if os.path.exists(id_file):
        with open(id_file, 'r') as f:
            result = f.read().strip()

    # Ask for the information if it does not.
    if not result:
        print('Please input the Playlist ID for', playlist_type)
        print('(Playlist ID can be found at the end of the web URL for the playlist)')
        result = input('Input --> ')
        # Save the input locally
        with open(id_file, 'w') as f:
            f.write(result)
    return result

def synchronize_playlist(sp, storage_loc, playlist_type):
    # This will look for the playlist id of the specified type, asking the user for input if it does not exist.
    # Then it will attempt to read that playlist id from spotify, and synchronize it locally as a CSV Fuke
    print_break()
    print('Beginning synchronization of', playlist_type + '.')
    track_data = []

    # Retrieve or have user input Playlist ID
    list_id = get_playlist_id(storage_loc, playlist_type)

    # Get the track list for Playlist ID
    try:
        results = sp.playlist_tracks(list_id)
        print(playlist_type, 'batch #1 received.')
    except Exception as e:
        print('Unable to retrieve track list:', e)
        print('Clearing saved playlist id')
        clear_local_file(storage_loc, playlist_type, 'Playlist ID')
        print('Terminating script.')
        sys.exit(1)

    tracks = results['items']
    batch = 2
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
        print(playlist_type, 'batch #' + str(batch), 'received.')
        batch += 1

    # Convert the JSON results so they can be read into a dataframe.
    for item in tracks:
        if item['track'] is None:
            continue

        track = item['track']

        # Compile track information
        track_info = {
            'album_id': track['album']['id'],
            'album_name': track['album']['name'],
            'artist_id': track['artists'][0]['id'] if track['artists'] else None,
            'artist_name': track['artists'][0]['name'] if track['artists'] else None,
            'track_id': track['id'],
            'track_name': track['name'],
            'popularity': track['popularity'],
            'duration_ms': track['duration_ms']
        }
        track_data.append(track_info)

    # Convert to dataframe and save to CSV.
    playlist_df = pd.DataFrame(track_data)
    playlist_file = os.path.join(storage_loc, playlist_type) + '.csv'
    playlist_df.to_csv(playlist_file, index=False)
    print(len(playlist_df), 'songs synchronized from', playlist_type, 'and saved to', playlist_file)

def get_sync_date(filepath):
    # Reads the file containing all known listening history and returns the maximum timestamp
    # value, which represents the last time the data a synchronized from Spotify.
    # Spotify can only return the very recent history, so complete history must be stored locally.

    default_timestamp = int(datetime(2025, 2, 12, 0, 0, 0).timestamp() * 1000)

    try:
        # Read the CSV
        df = pd.read_csv(filepath)

        # Check for column existence
        if ('played_at_timestamp' not in df.columns) or df.empty:
            print('*********** Timestamp column not found in listening history file.')
            max_ts = default_timestamp
        else:
            max_ts = df['played_at_timestamp'].max()

        sync_ts = max_ts

    except FileNotFoundError:
        print('*********** Listen history file not found.')
        sync_ts = default_timestamp

    except Exception as e:
        print('Error getting the timestamp history:', e)
        print('Default timestamp is being used.')
        sync_ts = default_timestamp

    return sync_ts

def dt_standardize(df, col_name):
    # ensures a df with col_name is in proper datetime format
    try:
        updated_df = df.copy()
        temp_col = pd.to_datetime(updated_df[col_name])
        updated_df[col_name] = temp_col.apply(
            lambda x: x.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z' if pd.notna(x) else x)
        return updated_df
    except Exception as e:
        print('Failed conversion of', col_name, 'to datetime.')
        return df

def format_timestamp(ts):
    # formats a timestamp in ms from the unix EPOCH to readable format in pacific time
    utc_dt = datetime.fromtimestamp(ts/1000, pytz.UTC)
    local_dt = utc_dt.astimezone(pytz.timezone('America/Los_Angeles'))
    return local_dt.strftime("%d-%b-%Y %H:%M %Z")

def ts_difference(ts1, ts2):
    # returns a string corresponding the the approximate amount of time between two timestamps
    dt1 = datetime.fromtimestamp(ts1/1000)
    dt2 =datetime.fromtimestamp(ts2/1000)

    # Ensure dt2 is always the later time.
    if dt1 > dt2:
        dt1, dt2 = dt2, dt1

    diff = dt2-dt1
    diff_seconds = diff.total_seconds()
    diff_minutes = round(diff_seconds / 60, 0)
    diff_hours = round(diff_minutes / 60, 0)
    diff_days = round(diff_hours / 24, 0)
    diff_months = round(diff_days / 30.44, 0)

    if diff_seconds < 60:
        return str(diff_seconds) + ' seconds'
    elif diff_minutes < 60:
        return '~' + str(diff_minutes) + ' minutes'
    elif diff_hours < 24:
        return '~' + str(diff_hours) + ' hours'
    elif diff_days < 30:
        return '~' + str(diff_days) + ' days'
    else:
        return '~' + str(diff_months) + ' months'

def get_recently_played(sp, filepath):
    # Function will return as much history as the API allows, between the most recent
    # and last-synchronized timestamps.
    lh_filename = os.path.join(filepath, 'listen_history.csv')

    # Retrieve the last known synchronized timestamp.
    prior_sync_ts = get_sync_date(lh_filename)


    # Spotify API will only return 50 songs at a time and only for a certain number of days.
    # Script starts with the most recent timestamp and works backwards.
    api_ts = int(datetime.now(pytz.UTC).timestamp() * 1000)

    print_break()
    print('Attempting to get play history between',
          format_timestamp(prior_sync_ts), 'and',
          format_timestamp(api_ts)), ' || ', ts_difference(prior_sync_ts, api_ts)

    # initialize local variables
    all_tracks = []  # empty track list
    more_tracks = True  # retrieve an additional batch of tracks
    batch = 0  # keep track of the number of batches we have retrieved from the API
    batch_repeat = 0

    while more_tracks:
        api_ts_at_start = api_ts
        batch = batch + 1
        print('Starting batch #', batch, 'for songs before:', format_timestamp(api_ts))

        # Return list of the 50 most recently played songs played prior to before_ts
        results = sp.current_user_recently_played(limit=50, before=api_ts)
        # results = sp.current_user_recently_played(limit=50)

        if not results['items']:
            break

        # Iterate through each track received, converting to values that will be appended to dataframe.
        for item in results['items']:

            # Get the timestamp
            played_at = item['played_at']
            played_at_dt = datetime.strptime(played_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            track_ts = int(played_at_dt.timestamp() * 1000)

            # Reset the API timestamp to earlier values.
            if track_ts < api_ts:
                # print('Track: Updating timestamp from', api_ts, 'to', track_ts)
                api_ts = track_ts

            # Check if we've gone too far back in time
            if api_ts < prior_sync_ts:
                more_tracks = False
                break

            # Add to our list
            track = item['track']
            track_data = {
                'track_name': track['name'],
                'artist_name': track['artists'][0]['name'],
                'album_name': track['album']['name'],
                'played_at': played_at,
                'played_at_timestamp': track_ts,
                'duration_ms': track['duration_ms'],
                'track_id': track['id'],
                'popularity': track['popularity'],
                'meta_batch': batch,
                'is_tracked_song': False  # used later when compared against the tracked playlist
            }
            all_tracks.append(track_data)
            # End of batch iteration loop.

        # Test if we need to retrieve another batch.
        if not more_tracks:
            break

        # Test if this api timestamp has changed since the last timestamp. When syncing play history from certain
        # sources, the played at timestamp for all songs can be identical. Otherwise the list of returned
        # songs will be identical and loop will iterate forever.

        if api_ts_at_start == api_ts and batch_repeat < 2:
            # print('Subtracting 1 minute from api:', api_ts, 'to', api_ts - 60000)
            api_ts = api_ts - 60000
            batch_repeat += 1
        elif batch_repeat >= 2:
            print('Breaking loop due to repeat batches with no updated timestamps')
            break
        else:
            # Sleep briefly to avoid hitting rate limits.
            time.sleep(1)
    # Batch Retrieval loop complete.

    # Declare the column list to be used in dataframes.
    column_list = ['track_name', 'artist_name', 'album_name', 'played_at', 'played_at_timestamp',
                   'duration_ms', 'track_id', 'popularity', 'meta_batch', 'is_tracked_song']

    # Convert api results into a dataframe.
    recent_tracks_df = pd.DataFrame(all_tracks, columns=column_list)

    # Read the complete running playlist into a dataframe.
    all_tracks_filename = os.path.join(filepath, 'all_tracked_songs.csv')
    tracked_playlist_df = pd.read_csv(all_tracks_filename)
    tracked_playlist_track_ids = set(tracked_playlist_df['track_id'])

    # Update the 'is_running_song' column in the recent plays to an accurate value.
    mask = recent_tracks_df['track_id'].notna() & recent_tracks_df['track_id'].isin(tracked_playlist_track_ids)
    recent_tracks_df.loc[mask, 'is_tracked_song'] = True

    # Restrict column output of dataframe and write to csv.
    recent_tracks_df = recent_tracks_df[column_list]
    recently_played_file = os.path.join(filepath, 'recently_played.csv')
    recent_tracks_df.to_csv(recently_played_file, index=False)
    print(len(recent_tracks_df), 'recently played songs retrieved and saved to', recently_played_file)
    return len(recent_tracks_df)
    # Function over.

def remove_remastered(str):
    # function takes a string that contains the 'remastered' title and removes it, allowing
    # for more accurate string comparisons.
    str_lower = str.lower()
    variations = ["(deluxe remastered version)",
                  "deluxe remastered version",
                  "remastered version",
                  "- remastered",
                  "(remastered)"
                  "remastered",
                  "remaster"]
    for variant in variations:
        str_lower = str_lower.replace(variant, '')

    # try regex matching:
    pattern = r'\s*[-–]?\s*[\(\[]?(?:remastered)(?:\s+\d{4})?[\)\]]?\s*'
    return re.sub(pattern, '', str_lower).strip()

def string_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def value_replace(filepath, filename, old_value, new_value, col_name='track_id'):
    # opens the specified file, replaces all instances of old value with new value in the specified column
    # saves teh file.
    fn = os.path.join(filepath, filename+ '.csv')
    df = pd.read_csv(fn)
    if col_name not in df.columns:
        print('!!! Replacement failed,', col_name, 'is not a valid column.')
    else:
        df[col_name] = df[col_name].replace(old_value, new_value)
        df.to_csv(fn)

def infer_updated_track_ids(storage_filepath, threshold=0.9):
    recent_fn = os.path.join(storage_filepath, 'recently_played.csv')
    recent_df = pd.read_csv(recent_fn)
    recent_df_orig = recent_df.copy()

    # Only progress if there are songs in recent listening history.
    if len(recent_df) > 0:
        # read dynamic playlist from local storage
        dynamic_fn = os.path.join(storage_filepath, 'dynamic_songs.csv')
        dynamic_df = pd.read_csv(dynamic_fn)
        print_break()
        print('Testing', len(recent_df),
              'recent songs for Spotify Substitutions, with a similarity threshold of', threshold)
        # Test the songs in recent history 1x1
        for r_id, recent_track in recent_df.iterrows():
            recent_track_id = recent_track['track_id']
            recent_track_name = remove_remastered(recent_track['track_name'])
            recent_track_artist = remove_remastered(recent_track['artist_name'])
            recent_track_album = remove_remastered(recent_track['album_name'])
            recent_track_duration = recent_track['duration_ms']

            # Test against the songs in the dynamic track 1x1
            for p_id, playlist_track in dynamic_df.iterrows():
                playlist_track_id = playlist_track['track_id']
                exact_match = recent_track_id == playlist_track_id

                # Exclude all the exact matches
                if not exact_match:
                    playlist_track_name = remove_remastered(playlist_track['track_name'])
                    playlist_track_artist = remove_remastered(playlist_track['artist_name'])
                    playlist_track_album = remove_remastered(playlist_track['album_name'])
                    playlist_track_duration = playlist_track['duration_ms']
                    duration_match_pct = abs(recent_track_duration - playlist_track_duration) / playlist_track_duration
                    name_score = string_similarity(playlist_track_name, recent_track_name)
                    artist_score = string_similarity(playlist_track_artist, recent_track_artist)
                    album_score = string_similarity(playlist_track_album, recent_track_album)

                    # When a potential match is detected, display relevant information and ask the user to accept/reject
                    if name_score > threshold or ((name_score > threshold/2 and duration_match_pct < 0.05) and
                             (album_score > threshold/2 or artist_score > threshold / 1.5)):
                        print('****** POTENTIAL REPLACEMENT NEEDED ******')
                        print('Track (', round(name_score, 2), ') ||', recent_track_name[:40],
                              '(r) vs', playlist_track_name[:40], '(p)')
                        print('Artist (', round(artist_score, 2), ') ||', recent_track_artist[:40],
                              '(r) vs', playlist_track_artist[:40], '(p)')
                        print('Album (', round(album_score, 2), ') ||', recent_track_album[:40],
                              '(r) vs', playlist_track_album[:40], '(p)')
                        print('Duration ||', int(recent_track_duration / 1000), '(r) vs',
                              int(playlist_track_duration / 1000), '(p) - pct:',
                              str(round(duration_match_pct*100,1)) + '%' )
                        accept_replacement = input('Accept replacement (Y/N) --> ')

                        # If the replacement is acceptable, swap the value across relevant files.
                        if accept_replacement == 'y' or accept_replacement == 'Y':
                            print('Swapping', playlist_track_id, 'for', recent_track_id)
                            value_replace(storage_filepath, 'rankings',
                                          playlist_track_id, recent_track_id)
                            value_replace(storage_filepath, 'dynamic_songs',
                                          playlist_track_id, recent_track_id)
                            value_replace(storage_filepath, 'all_tracked_songs',
                                          playlist_track_id, recent_track_id)
                            value_replace(storage_filepath, 'listen_history',
                                          playlist_track_id, recent_track_id)
                        # Else no replacement desired, go to next song in dynamic file
                    # Else below replacement threshold, go to next song in dynamic file
                # Else is already an exact match, skipping, go to next song in dynamic file.
            # Loop completed, go to next song in dynamic list.
        print('Spotify substitution testing complete.')

def infer_history(storage_filepath, ms_in_24_hours=86400000):
    # Compares the recently played history to the dynamically generated playlist.
    # Spotify won't necessarily return all songs listened to on a garmin watch, but we can 'infer'
    # the listening history by looking at recent playlist history, and seeing which
    # song was farthest down the playlist. The inference is that all songs played prior to that song were played
    # but requires that the user not enable shuffle or skip songs.

    # initialize the dynamic playlist and the recently played history.
    dyn_df = pd.read_csv(os.path.join(storage_filepath, 'dynamic_songs.csv'))
    recently_played_fn = os.path.join(storage_filepath, 'recently_played.csv')
    recent_df = pd.read_csv(recently_played_fn)
    print_break()
    print('Inferring history between', len(recent_df), 'recently played songs and the dynamic playlist.')

    # Limit recent history to only songs played on the tracked playlist
    tracked_df = recent_df[recent_df['is_tracked_song'] == True].copy()

    # Cutoff songs played more than a day prior to the most recently played song.
    most_recent_timestamp = tracked_df['played_at_timestamp'].max()
    most_recent_played_at = tracked_df['played_at'].max()
    cutoff_timestamp = most_recent_timestamp - ms_in_24_hours
    tracked_df_short = tracked_df[tracked_df['played_at_timestamp'] > cutoff_timestamp].copy()

    # Add the 'row number' or 'song position' to the dynamic playlist.
    dyn_df['position'] = range(len(dyn_df))

    # Iterate through track list to locate the song position of the recently played songs.
    track_positions = dyn_df.loc[dyn_df['track_id'].isin(tracked_df_short['track_id']), 'position']
    print(len(track_positions), 'recently played songs found on tracked playlist.')

    # Infer the play history as all records of the dynamic playlist <= than the max play history
    if len(track_positions) > 4:  #Only infer history if at least 4 recent tracked songs have been played.
        max_pos = track_positions.max()
        print('Inferring history for all songs on dynamic playlist before #' + str(max_pos))
        inferred_plays_df = dyn_df[dyn_df['position'] <= max_pos].copy()
        inferred_plays_df = inferred_plays_df.dropna(subset=['track_id']) # drop null records
        inferred_plays_df = inferred_plays_df.drop(['artist_id', 'album_id', 'position'], axis=1) # drop misc columns
        inferred_plays_df['meta_batch'] = 0  # batch is set to zero for inferred plays
        inferred_plays_df['is_tracked_song'] = True  # we know these are all running songs
        inferred_plays_df['played_at'] = most_recent_played_at # inferred songs all have the same timestamp.
        inferred_plays_df['played_at_timestamp'] = most_recent_timestamp
        inferred_filename = os.path.join(storage_filepath, 'inferred.csv')
        inferred_plays_df.to_csv(inferred_filename, index=False)
        print(len(inferred_plays_df), 'songs with inferred history and saved as', inferred_filename )

        # Combine the inferred history with recently played history
        combined_df = pd.concat([recent_df, inferred_plays_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['played_at_timestamp', 'track_id'], keep='first')
        combined_df.to_csv(recently_played_fn, index=False)
    else:
        print('No inferred history gathered.')

def merge_play_history(storage_filepath):
    # Merges the recent play history with the running play history file, removing the record of any song played
    # multiple times in a 5 minute timespan.

    # Read in the recent history.
    recent_fn = os.path.join(storage_filepath, 'recently_played.csv')
    recent_df = pd.read_csv(recent_fn)
    print_break()

    if len(recent_df) > 0:
        # Declaration of common columns the output file needs.
        print('Starting merge assessment for', len(recent_df), 'songs.')
        column_list = ['track_name', 'artist_name', 'album_name', 'played_at', 'played_at_timestamp',
                       'duration_ms', 'track_id', 'meta_batch', 'is_tracked_song']
        recent_df = recent_df[column_list]

        history_fn = os.path.join(storage_filepath, 'listen_history.csv')

        # Initialize play history and recent history
        history_df = pd.read_csv(history_fn)
        history_df = history_df[column_list]


        # Combine the two playlists
        merged_df = pd.concat([history_df, recent_df], ignore_index=True)

        # Sort dataframe by last played time. If multiple songs played at same time, sort by song.
        merged_df = merged_df.sort_values(by=['track_id', 'played_at'], ascending=[True, False])
        merged_df = merged_df.drop_duplicates(subset=['played_at_timestamp', 'track_id'])
        merged_df = merged_df.reset_index(drop=True)

        # Initialize clean list of songs
        cleaned_rows =[]

        # Iterate song-by-song through the dataframe.
        for i in range(len(merged_df)):
            if i == 0:
                cleaned_rows.append(merged_df.iloc[i])
                continue

            # Establish distinct rows for comparison
            current_row = merged_df.iloc[i]
            last_cleaned_row = cleaned_rows[-1]

            # Test to see if the song is the same, and if the timestamp is within 5 minutes
            song_match = current_row['track_id'] == last_cleaned_row['track_id']
            track_match = song_match and abs(current_row['played_at_timestamp']
                                             - last_cleaned_row['played_at_timestamp']) < 300000

            # Add the row to the cleaned rows list if criteria are met.
            if not track_match:
                cleaned_rows.append(current_row)

        # Create a list with all track ids in the current running playlist
        tracked_playlist_fn = os.path.join(storage_filepath, 'all_tracked_songs.csv')
        tracked_playlist_df = pd.read_csv(tracked_playlist_fn)
        tracked_track_ids = set(tracked_playlist_df['track_id'])

        # Convert cleaned list into a dataframe
        cleaned_df = pd.DataFrame(cleaned_rows)

        # History-correct values based on the current running playlist.
        mask = cleaned_df['track_id'].notna() & cleaned_df['track_id'].isin(tracked_track_ids)
        cleaned_df.loc[mask, 'is_running_song'] = True

        # Ensure output dataframe is clean & sorted.
        cleaned_df = cleaned_df[column_list]
        cleaned_df = cleaned_df.sort_values(by=['played_at', 'track_id'], ascending=[False, True])
        cleaned_df = cleaned_df.reset_index(drop=True)

        # Write dataframe to csv
        cleaned_df.to_csv(history_fn, index=False)
        print(len(recent_df), 'recently played songs merged with', len(history_df), 'songs of history.')
        print('When cleaned, ', len(cleaned_df), 'played songs remain in history.')
        print('Updated history saved to', history_fn)
    else:
        print('No recent history exists for merge.')

def convert_played_at_format(df):
    """
    Convert the 'played_at' column to ISO 8601 format with Z suffix ("%Y-%m-%dT%H:%M:%S.%fZ")
    Handles values that are already in the target format or in "%Y-%m-%d %H:%M:%S.%f" format
    """

    # Function to check if a string is already in the target format
    def is_already_formatted(x):
        if not isinstance(x, str):
            return False
        return 'T' in x and x.endswith('Z')

    # Create a mask for values already in the target format
    if 'played_at' in df.columns:
        already_formatted = df['played_at'].apply(lambda x: is_already_formatted(x))

        # Convert the values that need conversion
        # First, make a copy of the column
        new_values = df['played_at'].copy()

        # Only convert values that aren't already in the target format
        mask = ~already_formatted
        if mask.any():
            # Convert to datetime and then to the target format
            temp_dt = pd.to_datetime(df.loc[mask, 'played_at'])
            new_values.loc[mask] = temp_dt.apply(
                lambda x: x.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z' if pd.notnull(x) else None
            )

        # Assign the new values back to the DataFrame
        df['played_at'] = new_values

    return df

def star_review(cutoff_time, df):
    # asks the user for a new rating for any song with a rating of zero or played in the last 24 hours
    cutoff_time = cutoff_time - timedelta(hours=24)
    updated_df = df.copy()

    # Iterate through the dataframe
    for index, row in updated_df.iterrows():
        if row['star_rating'] == 0 or pd.to_datetime(row['last_played']) > cutoff_time:
            track_name = row['track_name']
            artist_name = row['artist_name']
            curr_rating = row['star_rating']

            # Get the user to input a new rating
            print('**** Star Rating Review ****')
            input_string = (track_name[:40] + ' by ' + artist_name[:40] + '|| Current rating: '
                            + str(curr_rating) + ' -->')
            new_rating = input(input_string)

            # Adjust to acceptable input patterns
            try:
                new_rating = int(new_rating)
            except:
                new_rating = curr_rating

            if new_rating is None:
                new_rating = curr_rating
            elif new_rating < 1:
                new_rating = 1
            elif new_rating > 5:
                new_rating = 5

            # update dataframe with new rating
            if new_rating != curr_rating:
                updated_df.at[index, 'star_rating'] = new_rating
    return updated_df

def star_plays(row):
    # Takes 1 row of data from the ranking file and returns a specific column depending on
    # the star value for the song in that column.

    # Get the star value
    star_value = row['star_rating']

    # Default any unrated tracks (star value = 0) to 5 star column
    if star_value == 0:
        star_value = 5

    # Determine the new column name
    col_name = str(star_value) + '_star_recent_plays'
    return row[col_name]

def update_rankings(storage_filepath):
    # Loads the play history and running files. Calculates listening stats by star level.
    # Asks users to update ratings for recently played and 0-star songs.
    # Writes an updated rankings file which is later used to re-write playlists.
    print_break()
    print('Updating dynamic ranking calculations.')
    rankings_fn = os.path.join(storage_filepath, 'rankings.csv')
    history_fn = os.path.join(storage_filepath, 'listen_history.csv')
    tracked_fn = os.path.join(storage_filepath, 'all_tracked_songs.csv')

    # Initialize the dataframes for ratings, listening history, and the tracked song playlist.
    rankings_df = pd.read_csv(rankings_fn)
    history_df = pd.read_csv(history_fn)
    tracked_df = pd.read_csv(tracked_fn)

    # Keep a record of any songs that have been removed from the running playlist.
    playlist_removals_file = os.path.join(storage_filepath, 'playlist_removals.csv')
    removals_df = pd.read_csv(playlist_removals_file)

    # Create a dataframe of songs ON the playlist BUT NOT IN the ratings file.
    tracks_to_add = tracked_df[~tracked_df['track_id'].isin(rankings_df['track_id'])]

    # Create a dataframe of songs that ARE in the ratings file, BUT NOT on the current playlist
    tracks_to_remove = rankings_df[~rankings_df['track_id'].isin(tracked_df['track_id'])]

    # Create a dataframe of only songs that are on BOTH the ratings file & current playlist.
    updated_ratings = rankings_df[rankings_df['track_id'].isin(tracked_df['track_id'])]

    # Add songs from the running playlist to the rating playlist with a default star value of zero.
    if not tracks_to_add.empty:
        print('Adding ', len(tracks_to_add), ' tracks to rankings')
        tracks_to_add['star_rating'] = 0
        common_cols = [col for col in rankings_df.columns if col in tracks_to_add.columns]
        tracks_to_add_subset = tracks_to_add[common_cols]

        for col in rankings_df.columns:
            if col not in tracks_to_add.columns:
                tracks_to_add_subset[col] = np.nan

        updated_ratings = pd.concat([updated_ratings, tracks_to_add_subset[rankings_df.columns]],
                                    ignore_index=True)

    # Remove songs from the rating file that are no longer on the running playlist.
    if not tracks_to_remove.empty:
        removals_df =pd.concat([removals_df, tracks_to_remove], ignore_index=True)
        removals_df.to_csv(playlist_removals_file, index=False)

    # Ensure datetime format compliance
    history_df = dt_standardize(history_df, 'played_at')

    # Restrict to just the relevant columns
    column_list = ['track_id', 'track_name', 'artist_name', 'duration_ms', 'star_rating']
    updated_ratings = updated_ratings[column_list]

    # Determine the max played at time for any given track.
    last_played = history_df.groupby('track_id')['played_at'].max().reset_index()
    last_played.rename(columns={'played_at': 'last_played'}, inplace=True)
    last_played = dt_standardize(last_played, 'last_played')

    # Merged last played information back into ratings file.
    updated_ratings = updated_ratings.merge(last_played, on='track_id', how='left')

    # intervals = [5: 14, 30, 60, 90, 180]
    # Create a dictionary that corresponds to the star values and the days of recent play history to calculate
    intervals = {5: 14, 4: 30, 3: 60, 2: 90, 1: 180}

    # Set the current UTC timestamp so we have a point of comparison
    today = datetime.now(pytz.UTC)

    # Iterate through the dictionary and build columns
    for star_ranking, days_value in intervals.items():
        # Set the day I'm comparing against.
        days_ago = today - timedelta(days = days_value)

        # Limit the dataframe to just songs played more recently than that date.
        recent_plays = history_df[pd.to_datetime(history_df['played_at']) >= days_ago]

        # Count the number of times the track was played in the last x days
        play_count = recent_plays.groupby('track_id').size().reset_index()

        # Dynamically name the new column
        col_name = str(star_ranking) + '_star_recent_plays'
        play_count.rename(columns={0: col_name}, inplace=True)

        # Merge the new columns with the existing dataframe.
        updated_ratings = updated_ratings.merge(play_count, on='track_id', how='left')

    # Ensure all songs have a star rating. Default to zero.
    updated_ratings['star_rating'] = updated_ratings['star_rating'].fillna(0)

    updated_ratings = star_review(today, updated_ratings)

    # Set a new column to pull in a specific column value that depends on the star value.
    updated_ratings['star_plays'] = updated_ratings.apply(star_plays, axis=1)

    # Ensure all songs have a last-played date.
    if 'last_played' in updated_ratings.columns:
        updated_ratings['last_played'] = pd.to_datetime(updated_ratings['last_played'])
    else:
        # If last_played doesn't exist, create a placeholder very old date
        updated_ratings['last_played'] = pd.to_datetime('2024-01-01')


    # Ensure all songs have a duration value.
    if 'duration_ms' not in updated_ratings.columns:
        updated_ratings['duration_ms'] = 0

    # Perform cleaning tasks on final ratings dataframe.
    updated_ratings = convert_played_at_format(updated_ratings)
    updated_ratings['star_plays'] = updated_ratings['star_plays'].fillna(0)
    updated_ratings['last_played'] = updated_ratings['last_played'].fillna('2020-01-01T01:01:01.001Z')
    updated_ratings = dt_standardize(updated_ratings, 'last_played')
    updated_ratings['random_num'] = np.random.randint(1,len(updated_ratings) * 2, size=len(updated_ratings))

    # Sort the dataframe by the least-played songs based on star values, then a bunch of tiebreakers.
    sorted_ratings = updated_ratings.sort_values(by =['star_plays', 'random_num'],
                                                 ascending=[True, True])

    # Add a ranking for the new song order.
    sorted_ratings['ranking'] = range(1, len(sorted_ratings) + 1)

    # Export the updated ratings file.
    sorted_ratings.to_csv(rankings_fn, index=False)
    print('Updated rankings complete and saved to', rankings_fn)

def update_playlist(sp, storage_path, playlist_name, num_songs=999):
    # Initialize the ratings file as a dataframe
    ratings_fn = os.path.join(storage_path, 'rankings.csv')
    ratings_df = pd.read_csv(ratings_fn)

    # Initialize the track list
    track_ids = []

    # Only retrieve valid tracks and add to list.
    for track_id in ratings_df['track_id']:
        if pd.isna(track_id):
            continue

        track_id = str(track_id).strip()
        track_ids.append(track_id)

    # Obtain the playlist ID of the set we are updating
    list_id = get_playlist_id(storage_path, playlist_name)

    # Remove all songs from the existing, specified playlist.
    sp.playlist_replace_items(list_id, [])

    # Reduce the tracks to the specified number of songs.
    tracks_to_load = track_ids[:num_songs]
    print_break()
    print('Updating', playlist_name, 'with ', len(tracks_to_load), 'songs.')

    # Initialize the batch size in case < 100 songs are requested
    if num_songs < 100:
        batch_size = num_songs
    else:
        batch_size = 100

    # Batch the upload if longer than 100 items
    for i in range(0, len(tracks_to_load), batch_size):
        batch = track_ids[i:i+batch_size]
        sp.playlist_add_items(list_id, batch)

    print('Finished updating', playlist_name, 'with ', len(tracks_to_load), 'songs.')




