from mutagen.mp3 import MP3


if __name__ == '__main__' :
    audio = MP3("../songs/04 Fix You.mp3");
    print audio.info.length
    print audio.info.bitrate
