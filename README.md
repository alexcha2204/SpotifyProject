# ReleaseRadarClone

## Problem Statement
Spotify offers two playlists, **New Music Friday** and **Release Radar**, that update weekly but serve different purposes. New Music Friday features newly released music throughout the week, while Release Radar curates a personalized list of songs based on a user's listening history, including artists they know and recommendations. 

As a constant Spotify user, I've noticed inconsistencies between these playlists, where certain artists appear on one but not the other. This creates a challenge for users who prefer a unified playlist experience, where all desired songs, artists, and genres are consolidated instead of being scattered across two playlists.

## Solution
The goal of this project is to create **ReleaseRadarClone**, a single playlist that compiles the best song recommendations based on a user's liked songs. By analyzing the relationships between artists and genres, the project aims to deliver a personalized music experience.

## Process
1. **Create a Spotify App:**
   - Visit the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) to create a Spotify App.
   - Set up the app via localhost and obtain the necessary API keys for development.

2. **Data Retrieval:**
   - Use the API keys to extract data from the user's liked songs, which includes:
     - `artist_name`
     - `artist_id`
     - `first_added`
     - `first_song`
     - `first_album`
     - `first_album_type`
     - `last_added`
     - `last_song`
     - `last_album`
     - `last_album_type`
     - `main_songs_count`
     - `featured_songs_count`
     - `liked_songs_count`
   - Additionally, create a JSON file that contains all genres recorded.

3. **Genre Analysis:**
   - Analyze the genres JSON file to determine the most common genres using frequency and Inverse Document Frequency (IDF) weights.

4. **Artist Relevance:**
   - Identify relevant artists based on the genres and filter out any irrelevant genres. 
   - Match artists by genres and retain only those that are matched.

5. **Trend Analysis:**
   - For each artist, identify common trends such as:
     - The last time a song was liked.
     - The number of songs liked as a main or featured artist.
   - This information helps assess whether recommendations are needed.

6. **Future Work:**
   - The project is ongoing, and I welcome any inquiries for further details about the development process and features!
