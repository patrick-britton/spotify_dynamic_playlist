import spotify_functions as sf
#####################################################################################################
# To use this script, you must first create an application and obtain the client id & secret tokens
# from developer.spotify.com.
# This script will prompt you for those two values and save them locally.
# Update with the file directory where you'd like your credentials saved and your local files stored.
credential_location = 'C:/Users/rickb/PycharmProjects/credentials/'
local_file_storage_location = 'C:/Users/rickb/PycharmProjects/spotify_file_storage/'
sf.local_initialization_check(credential_location, local_file_storage_location)
# if the above locations do not exist, they will be created by the above function.
#####################################################################################################
#####################################################################################################
# Script can assume songs have been played, if multiple songs from a playlist have been played recently
# but Spotify doesn't have the complete history. For example, not every song from Garmin is tracked.
infer_play_history = True
# Set infer_play_history to False if you don't want to augment your listening history with assumptions.
#####################################################################################################


client = sf.spotify_login(credential_location)
sf.synchronize_playlist(client, local_file_storage_location, 'all_tracked_songs')
sf.synchronize_playlist(client, local_file_storage_location, 'dynamic_songs')
recent_count = sf.get_recently_played(client, local_file_storage_location)

if recent_count > 0:
    sf.infer_updated_track_ids(local_file_storage_location, 0.8)
    if infer_play_history:
        sf.infer_history(local_file_storage_location)
    sf.merge_play_history(local_file_storage_location)

sf.update_rankings(local_file_storage_location)
sf.update_playlist(client, local_file_storage_location, 'all_tracked_songs')
sf.update_playlist(client, local_file_storage_location, 'dynamic_songs', 50)






