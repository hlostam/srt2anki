import re
from pathlib import Path

import cchardet as chardet
import pandas as pd
import fasttext
import srt
import py.io
import urllib.request

from srt2anki import analysis, anki

LANG_TRANSLATE_MODEL_PATH = './models/lid.176.ftz'

############################################################
# Subtitle parse
############################################################
def get_srt_df(srt_path, srt_encoding, language_short=None):
    text = read_srt(srt_path, srt_encoding)
    data = srt2text(text)
    if language_short is None:
        language_short = detect_text_language(data)
    lemmatised = analysis.lemmatise_spacy(data, language_short)
    
    return lemmatised, language_short

def get_srt_df_cached(srt_path, srt_encoding, language_short=None):
    print("get_srt_df_cached")
    if language_short is None:
        language_short = detect_file_language(srt_path)
    srt_path_noext = srt_path[:-4]
    lemmatised_csv_path = srt_path_noext+'.lemma.csv'
    try:
        lemmatised = pd.read_csv(lemmatised_csv_path)
    except Exception as e:
        print('Loading srt slow')
        lemmatised, language_short = get_srt_df(srt_path, srt_encoding, language_short)
        lemmatised.to_csv(lemmatised_csv_path, index=False)

    return lemmatised, language_short

def detect_file_encoding(file_path):
    with open(file_path, "rb") as f:
        msg = f.read()
        result = chardet.detect(msg)
    return result['encoding']

def get_fasttext_model():
    if not Path(LANG_TRANSLATE_MODEL_PATH).exists():
        url = 'https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin'
        urllib.request.urlretrieve(url, LANG_TRANSLATE_MODEL_PATH)
    # capture = py.io.StdCaptureFD(out=False, in_=False)
    model = fasttext.load_model(LANG_TRANSLATE_MODEL_PATH)
    # out, err = capture.reset()
    return model

def detect_text_language(text):
    text = re.sub('\W+',' ', text).replace('\n', '')
    model = get_fasttext_model()
    guess = model.predict(text, k=1)
    lang = guess[0][0].replace('__label__','')
    return lang

def detect_file_language(file_path, encoding=None):
    if encoding is None:
        encoding = detect_file_encoding(file_path)
    with open(file_path, encoding=encoding) as f:
        text = f.read()
    return detect_text_language(text)

def read_srt(srt_file_path, encoding=None):
    if encoding is None:
        encoding = detect_file_encoding(srt_file_path)
    with open(srt_file_path, encoding=encoding, errors='replace') as f:
        text = f.read()
    return text

def srt2text(text):
    parsed = srt.parse(text)
    parsed = list(parsed)
    parsed_list = [ anki.cleanhtml(x.content) for x in parsed]
    
    data = "\n".join(parsed_list)

    data = data.replace("- ",'')
    data = data.replace("...",' ')
    data = data.replace('\n', ' ')
    data = data.replace('#', '')
    
    data = re.sub('\s+',' ', data)

    return data

def load_txt(file_path):
    with open(file_path, 'r') as f:
        data = re.sub('\W+',' ', f.read()).replace('\n', '')
    return data