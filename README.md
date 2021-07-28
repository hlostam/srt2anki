# srt2anki
Create list of words to learn for a movie based on your anki knowledge.


## Install
1. `make venv`
2. `source ./bin/venv/activate` OR `venv`
   - Activating the virtual environment, `venv` is alias that can be created in your shell
3. ```pip install requirements.txt```
4. ```wget -O ./models/lid.176.bin https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin```
   - Download fasttext model to detect the language of the file:
    

## Usage
1. ```cp config.ini.template config.ini``` and edit the Anki properties
2. ```python main.py PATH_TO_SRT.srt```


## Tools used
- [cchardet](https://github.com/PyYoshi/cChardet) - detect the file encoding of the subtitles
- [fasttext](https://fasttext.cc/) - detection of the subtitles language
- [pycountry](https://pypi.org/project/pycountry/) - linking countries and their acronyms for language detections
- [srt](https://pypi.org/project/srt/) - parsing the subtitles 
- [Spacy](https://spacy.io/models/it) - lemmatisation 
- [genanki](https://github.com/kerrickstaley/genanki) - export Anki pacakge 

## (Not Needed) How to export Anki file
1. Open Anki Desktop
2. Ensure that it is synchronised (Sync)
3. File -> Export
    - Export format: *.apkg
    - Include: (select your deck)
4. Export