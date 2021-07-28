import cchardet as chardet
from ankipandas import Collection
import genanki
import pandas as pd
import re
# import unicodedata
from pathlib import Path
from ankisync2.apkg import Apkg
from ankisync2.anki21 import db
from srt2anki import analysis

import tempfile
import zipfile

############################################################
# Anki functions
############################################################
def get_anki_df(anki_path, language_short, card_deck=None, anki=None):
    if anki is not None:
        print("Anki loaded")
    elif(Path(anki_path).suffix == '.apkg'):
        print("Loading APKG:")
        anki = load_apkg(anki_path)
    else:
        print("Loading Anki collection")
        anki = parse_anki(load_anki(anki_path, card_deck))
    anki_together  = ' '.join(anki)
    anki_df = analysis.lemmatise_spacy(anki_together, language_short)[['word']]
    anki_df = anki_df.append(pd.DataFrame({'word':anki})).drop_duplicates()
    anki_df['is_anki'] = 1
    return anki_df

def get_anki_df_cached(anki_path, language_short, card_deck, 
                       anki_csv_path = 'anki.lemma.csv'):
    try:
        anki_df = pd.read_csv(anki_csv_path)
    except Exception as e:
        anki_df = load_anki_slow(anki_path, language_short, card_deck)
        anki_df.to_csv(anki_csv_path, index=False)
    return anki_df

def load_anki(anki_path, card_deck):
    col = Collection(anki_path)
    cards = col.cards[col.cards.cdeck == card_deck].copy()
    cards_merged = (cards
        .merge(col.notes, left_on='nid', right_index=True).copy()
    )
    return cards_merged

def parse_anki(df_anki):
    set_words = set([word[0] for word in df_anki.nflds])
    set_words = [cleanhtml(word.lower()) for word in set_words]
    return set_words

def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleaned = raw_html.replace('&nbsp;', '')
    cleantext = re.sub(cleanr, '', cleaned)
    return cleantext

def rm_tree(pth: Path):
    for child in pth.iterdir():
        if child.is_file():
            child.unlink()
        else:
            rm_tree(child)
    pth.rmdir()

def get_proper_anki_collection(archive):
    for name in ['anki21','anki20','anki2']:
        try:
            d = archive.read('collection.anki21')
            return d
        except Exception:
            pass
    raise Exception("Anki collection not found")

def load_apkg(file_path):
    print("load_apkg")
    archive = zipfile.ZipFile(file_path,'r')
    d = get_proper_anki_collection(archive)
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(d)
        tmp_file_name = f.name
    db.database.init(tmp_file_name)
    words = [ c.flds[0] for c in db.Notes.select()]
    words_clean = [cleanhtml(word.lower()) for word in words]
    Path(tmp_file_name).unlink()
    
    return words_clean

# def load_apkg(file_path):
#     print("load_apkg")
    
#     path = Path(file_path)
#     if not path.exists():
#         raise Exception("The file does not exists:{}".format(file_path))
    
#     # This exports the zip to the directory 
#     apkg = Apkg(path)
#     iter_apkg = iter(apkg)
    
#     name = path.stem
#     apkg_dir = Path(name)
#     if not apkg_dir.is_dir():
#         raise Exception("The {} is not a directory".format(apkg_dir))
#     anki20 = "./"+name+"/collection.anki20"
#     anki21 = "./"+name+"/collection.anki21"
#     anki2 = "./"+name+"/collection.anki2"
#     if Path(anki21).exists():
#         file = anki21
#     elif Path(anki20).exists():
#         file = anki20
#     else:
#         file = anki2
#     db.database.init(file)

#     words = [ c.flds[0] for c in db.Notes.select()]
#     words_clean = [cleanhtml(word.lower()) for word in words]
    
#     apkg.close()
#     rm_tree(apkg_dir)

#     return words_clean


# Export
def generate_anki_id(string):
    return abs(hash(string)) % (10 ** 10)

def generate_deck(df, deck_name):
    deck_name = deck_name.replace(" ","")
    deck = genanki.Deck(
        generate_anki_id(deck_name),
        deck_name)

    for row in df.to_dict('records'):
        deck.add_note(genanki.Note(
            model=genanki.BASIC_AND_REVERSED_CARD_MODEL,
            fields=[row['word'], 'TODO'],
            tags = [deck_name]
            )
        )

    file_path = deck_name + ".apkg"
    deck.write_to_file(file_path)
    
    return file_path
