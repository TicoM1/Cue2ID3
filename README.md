# Cue2ID3

**Cue2ID3**, as the name implies, will help you convert `.cue` sheets for your MP3 files to ID3 chapter tags. This is done based on the [ID3v2 Chapter Frame Addendum](https://id3.org/id3v2-chapters-1.0).

I welcome any feedback or suggestions.

## Use Case

Ripping software (e.g. foobar2000) typically allows you to rip audiobooks and other long audio files as a single file, which is easier to manage than splitting the audio into separate chapter files. However, these programs rarely support ID3v2 chapter tags and instead create a `.cue` sheet.

With many audiobook players (e.g. Sirin Audiobook Player) supporting ID3 chapters, you can enjoy the benefits of chapters while managing just one file – and still retain backwards compatibility with any device that relies on MP3s. You only need to transfer the chapter information from the cue sheets into the MP3's ID3 tags.

## Prerequisites (basically only Python3)

- **Python 3:**
- **Tkinter:** native GUI toolkit for Python (just double-click the script to open the program).
- **Mutagen:** Used for editing ID3 tags. The script will automatically pip install Mutagen on the first run if you want to.  
  For more details, see the [Mutagen ID3 v2 Chapters documentation](https://mutagen-specs.readthedocs.io/en/latest/id3/id3v2-chapters-1.0.html).

## Usage

Double click the script to run it. For verbose debug outputs, just run the script from console.
The GUI is self explanatory and also shows some descriptive text to make it independently understandable from this Readme.
The program offers two modes:

- **Single Mode:**  
  Will allow you to pick an mp3 and assume a cue-sheet with the same name. (E.g. Audio.mp3 and audio.mp3.cue).

- **Folder Mode:**  
  Folder mode will take a path as input and (non-recursively) scan that folder for matching pairs of .mp3 and .cue files.

In both cases the original file will get the new ID-tags. Before processing a backup file of the mp3 is created. After success the .bak as well as the .cue file are deleted.

## Planned Changes

- Making the deletion of the `.bak` and `.cue` files optional.
- Further enhancements based on user feedback.

---

Feel free to contribute, submit issues, or suggest enhancements!
