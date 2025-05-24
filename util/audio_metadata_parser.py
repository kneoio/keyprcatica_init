# audio_metadata_parser.py

import os
import mutagen
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.easyid3 import EasyID3


class AudioMetadataParser:
    def __init__(self, logger):
        self.logger = logger

    def parse_metadata(self, file_path):
        artist = None
        title = None
        album = None
        filename = os.path.basename(file_path)

        try:
            if filename.lower().endswith(".mp3"):
                try:
                    audio = EasyID3(file_path)
                    if 'artist' in audio: artist = audio['artist'][0]
                    if 'title' in audio: title = audio['title'][0]
                    if 'album' in audio: album = audio['album'][0]
                except ID3NoHeaderError:
                    self.logger.debug(f"No EasyID3 tags for MP3 {filename}. Trying full mutagen load.")
                except Exception as e_easyid3:
                    self.logger.warning(f"EasyID3 failed for {filename}: {e_easyid3}. Trying general load.")

            if not (artist and title and album) or not filename.lower().endswith(".mp3"):
                audio_obj = mutagen.File(file_path, easy=False)
                if audio_obj is None:
                    self.logger.warning(f"Mutagen could not recognize file type for {filename}.")
                    return {"artist": None, "title": None, "album": None}

                if isinstance(audio_obj, MP3):
                    if not artist and 'TPE1' in audio_obj: artist = str(audio_obj['TPE1'].text[0]) if audio_obj[
                        'TPE1'].text else None
                    if not title and 'TIT2' in audio_obj: title = str(audio_obj['TIT2'].text[0]) if audio_obj[
                        'TIT2'].text else None
                    if not album and 'TALB' in audio_obj: album = str(audio_obj['TALB'].text[0]) if audio_obj[
                        'TALB'].text else None
                elif isinstance(audio_obj, WAVE) and audio_obj.tags:
                    if not artist:
                        if 'ARTIST' in audio_obj.tags:
                            artist = str(audio_obj.tags['ARTIST'][0])
                        elif 'IART' in audio_obj.tags:
                            artist = str(audio_obj.tags['IART'][0])
                    if not title:
                        if 'TITLE' in audio_obj.tags:
                            title = str(audio_obj.tags['TITLE'][0])
                        elif 'INAM' in audio_obj.tags:
                            title = str(audio_obj.tags['INAM'][0])
                    if not album:
                        if 'ALBUM' in audio_obj.tags:
                            album = str(audio_obj.tags['ALBUM'][0])
                        elif 'IPRD' in audio_obj.tags:
                            album = str(audio_obj.tags['IPRD'][0])

                if not artist and 'artist' in audio_obj:
                    artist_val = audio_obj.get('artist')
                    if isinstance(artist_val, list) and artist_val:
                        artist = str(artist_val[0])
                    elif isinstance(artist_val, str):
                        artist = artist_val
                if not title and 'title' in audio_obj:
                    title_val = audio_obj.get('title')
                    if isinstance(title_val, list) and title_val:
                        title = str(title_val[0])
                    elif isinstance(title_val, str):
                        title = title_val
                if not album and 'album' in audio_obj:
                    album_val = audio_obj.get('album')
                    if isinstance(album_val, list) and album_val:
                        album = str(album_val[0])
                    elif isinstance(album_val, str):
                        album = album_val

            if artist and artist.strip().lower() in ["unknown artist", "unknown", "various artists"]: artist = None
            if title and title.strip().lower() in ["unknown title", "unknown", "untitled"]: title = None
            if album and album.strip().lower() in ["unknown album", "unknown", "various artists",
                                                   "untitled"]: album = None

            artist = artist.strip() if artist else None
            title = title.strip() if title else None
            album = album.strip() if album else None

            if artist or title or album:
                self.logger.info(f"Metadata parsed for {filename}: Artist='{artist}', Title='{title}', Album='{album}'")
            else:
                self.logger.info(f"No specific artist/title/album metadata found in {filename}.")

            return {"artist": artist, "title": title, "album": album}

        except mutagen.MutagenError as e:
            self.logger.warning(f"Mutagen error parsing metadata for {filename}: {e}.")
            return {"artist": None, "title": None, "album": None}
        except Exception as e:
            self.logger.error(f"Unexpected error parsing metadata for {filename}: {e}")
            return {"artist": None, "title": None, "album": None}