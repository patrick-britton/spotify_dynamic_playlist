# spotify_dynamic_playlist
Problem statements this script seeks to solve:

1. I like to listen to music while running, and have over 400 songs in a spotify playlist for that purpose. I seem to hear the same songs more frequently than I might expect.
2. I don't believe Spotify's shuffle algorithm (or maybe it's my garmin watch) is truly random.
3. Spotify doesn't seem to have any way to re-sort a playlist based on when I last listened to the song
4. Spotify has no user-rating system for me to declare "how much" like like any particular song.
5. Spotify has no "self-service" dynamic-playlist generating capability.
  
v0.0 Application features

1. Download my entire listening history from Spotify
2. Download a playlist of specific songs
3. Calculate basic listening stats for songs on that playlist.
4. Create a local "star rating" system
5. Update the playlist order based on a combination of the star rating and playlist stats.

How I use this in real life:
1. I have two playlists in Spotify, one representing all the songs I like listening to while running, and the other being a placeholder for the dynamic sorting that the script will do.
2. I sync the dynamic playlist to my garmin watch. I have this set to 50 songs to avoid long sync times, but this can be extended to whatever your comfortable with.
3. I run, listening to the dynamic playlist in default order (no shuffle).
4. After the run, I sync the watch with spotify (this usually happens automatically when plugging it in to charge with a wifi network the watch can connect to).
5. After the sync, I execute the script -- where I am prompted to re-verify the ranking I have for any song I listened to on the run.
6. After the script execution, I re-sync the dynamic playlist with my Garmin watch, and am ready to run again with a new list of songs I haven't heard recently!

Libraries used: sys, os, time, datetime, pandas, pytz, difflib, numpy, re -- and of course big thanks to the authors of Spotipy that made the communication between Spotify and my local machine easy.

To make this work:

1. You must first setup an application for your Spotify account using developer.spotify.com. This will give you visibility to your client_secret and client_id that allows you to login. You will also need to declare a redirect URI in the application. Default redirect URI can be: http://127.0.0.1:3000
3. Install the libraries listed above.
4. Sync spotify_functions.py to your local machine. This script does all the behind the scenes processing & logic.
5. Sync update_dynamic_playlist.py to your local machine. This script goes through the steps 1x1. 
6. Edit the update_dynamic_playlist.py file with local storage locations for your credentials and playlist, rating, and listening history files. (Lines 7 & 8)

Fun challenges/limitations discovered along the way that made this project interesting:

1. Spotify only returns your *very* recent listening history. You can request the full listening history through your account page, and it will be available to download a few days later. Either way, we need to save the listening history and append to it over time.
2. Spotify returns an *incomplete* listening history -- at least when syncing with a Garmin Fenix 6 watch. This means I need to infer what I've heard based on how far into the playlist I listened on any given run.
3. Spotify plays *different* songs than what may be on your playlist. This again may be due to the limitations of listening from a watch, but each song has a unique 'track_id' value. I've noticed the song that gets played is sometimes a "remastered" version or else the 'mono' version of a 'stereo' song. Leaning into conspiracy theory, it may be selecting tracks that have lower-license fees than the ones I put on a playlist. So I'll need some way to detect when Spotify has done the old switcheroo on me and make the appropriate changes to the appropriate playlists and listening history.


How the update_dynamic_playlist works:

1. Establishes a successful connection to the spotify API, with the appropriate permissions to access user information and edit playlists. On the first execution, user will be prompted to enter their client_id, client_secret, and redirect_uri values that can be obtained from developer.spotify.com/dashboard. These values are saved locally in a destination specified in line 7 of the update_dynamic_playlist.py file. If login ever fails for any reason, the locally-stored credentials will be wiped and user will be asked to reenter.
2. Downloads your 'all_tracked_songs' playlist to a local csv file. This can be any playlist you'd like -- each playlist has a unique id obtainable from the URL for that playlist. On the first execution, script will prompt the user to enter this unique_id. The 'all_tracked_songs' should represent the entire list of all songs you'd like to dynamically sort.
3. Downloads your 'dynamic_songs' playlist to a local csv file. Garmin watches have a limitation on the # of songs a playlist can have and still play without errors. I don't know what the limit is, but I try not to go above 100 songs. This playlist is the one you should listen to, and ideally listen to with "shuffle off."
4. Downloads all songs you've listened to recently, regardless of what playlist they may or may not appear on. It calls the api for songs between the current time and the most-recently-played timestamp from your locally saved history.
5. Compares songs on the recently played list to the dynamic song list, to see if Spotify has swapped the song from your playlist with an alternate version. Script uses SequenceMatcher from difflib library to compare track names, artists, albums, and durations to detect similarities. If a similarity is detected, user is prompted to accept the swap. If swap is accepted, the new track_id is written across all the local csvs.
6. Checks the recently played history against the dynamic playlist, discovering how far down the playlist you reached. Based on the song position on your playlist, it assumes all prior songs have been listened to. If you aren't listening to the 'dynamic' playlist in order, or don't want or need this option, set infer_play_history = False in line 15 of the script.
7. Merges the recently played history with the listening history file stored locally. If the same song is listened to multiple times in a 5 minute span, it records only a single play.
8. Calculates listening stats for all songs on the 'all_tracked_songs' playlist. Merges the all_tracked_songs playlist with your ranking file, and creates a new, dynamically created ranking based on the listening stats.
9. Updates the 'all_tracked_songs' playlist on Spotify with the new order, as determined in the prior step.
10. Updates the 'dynamic_songs' playlist on Spotify with the top X songs, as specified by the user.

How the dynmamic rankings work:

If you haven't ranked your songs, don't worry -- all songs recieve a zero-star ranking by default, and you will be prompted to update these when you run the script for the first time. It may be easier to locate the 'rankings.csv' file and edit that en-masse in excel. 

Script calculates how recently you listened to any given track. it also calculates how many times you've listened to a song in the last 14, 30, 60, 90, or 180 days, depending on if the song is rated 5, 4, 3, 2, or 1 stars, respectively. It will then sort the playlist based on the # of times you've played it based on the song rating, when you've last heard the song, and a random number (to break ties). So if you've listened to a 5-star song 3 times in the last 14 days, and a 4-star song 2 times in the last 30 days, and a 1 star song only once in the last 180 days, the play list will put the 1-star song first, the 4-star song second, and the 5-star song last. Over enough listens, this will play the 5-star songs more frequently than all the others, but still in a somewhat random order and keep you from hearing them within a certain timeframe. If you want to edit the day-values, look for the 'intervals' dictionary defined in the "update rankings" function within spotify_functions.py.

