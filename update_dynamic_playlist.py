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
shuffle_off = True
# shuffle_off parameter can infer listening history for all songs heard from the tracked playlist. For use in situations
# when streaming from a Garmin watch where the complete play history is not tracked. This will only return accurate
# results if the playlist is not listened to in shuffle order.
# True value will infer the play history, False value will return only the explicit results from the api call.
count_tracked_plays_only = True
# count_tracked_plays_only gives the option to consider songs played directly from the tracked playlist (instead
# of all sources) if it detects that the tracked playlist has been listened to. Please note that this only going to
# make a determination of "is listening history from tracked playlist" based on overlap between the listening history
# and the tracked playlist. Thus, it will be imperfect, especially if you are listening with shuffle enabled.
# a True value will discount any plays from the listening history that don't seem to be from the tracked playlist
# a False value will include all plays of a song regardless of source playlist.
#####################################################################################################


client = sf.spotify_login(credential_location)
sf.synchronize_playlist(client, local_file_storage_location, 'all_tracked_songs')
sf.synchronize_playlist(client, local_file_storage_location, 'dynamic_songs')
recent_count = sf.get_recently_played(client, local_file_storage_location, count_tracked_plays_only)

if recent_count > 0:
    sf.infer_updated_track_ids(local_file_storage_location, 0.8)
    sf.infer_history(local_file_storage_location, shuffle_off)
    sf.merge_play_history(local_file_storage_location)

sf.update_rankings(local_file_storage_location, count_tracked_plays_only)
sf.update_playlist(client, local_file_storage_location, 'all_tracked_songs')
sf.update_playlist(client, local_file_storage_location, 'dynamic_songs', 50)






