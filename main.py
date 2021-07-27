import os, re, sys
import itertools
import logging
from itertools import dropwhile
from collections import Counter

import pandas as pd
import argparse
import configparser

import cchardet as chardet
import srt
from ankipandas import Collection
import genanki
import unicodedata
from pycountry import languages

import spacy
import fasttext

############################################################
# Subtitle parse
############################################################

def detect_file_encoding(file_path):
    with open(file_path, "rb") as f:
        msg = f.read()
        result = chardet.detect(msg)
    return result['encoding']

def get_fasttext_model():
    import py.io
    capture = py.io.StdCaptureFD(out=False, in_=False)
    model = fasttext.load_model(LANG_TRANSLATE_MODEL_PATH)
    out, err = capture.reset()
    return model

def detect_file_language(file_path, encoding=None):
    if encoding is None:
        encoding = detect_file_encoding(file_path)
    with open(file_path, encoding=encoding, errors='replace') as f:
        text = re.sub('\W+',' ', f.read()).replace('\n', '')
    model = get_fasttext_model()
    guess = model.predict(text, k=1)
    lang = guess[0][0].replace('__label__','')
    return lang

def srt2text(srt_file_path, encoding=None):
    if encoding is None:
        encoding = detect_file_encoding(srt_file_path)

    import srt
    with open(srt_file_path, encoding=encoding, errors='replace') as f:
        text = f.read()
        parsed = list(srt.parse(text))
    parsed_list = [ x.content for x in parsed]

    txt_file_path = srt_file_path[:-4] + '.txt'
    with open(txt_file_path, 'w') as f:
        for line in parsed_list:
            f.write(line)
    return txt_file_path

def load_txt(file_path):
    with open(file_path, 'r') as f:
        data = re.sub('\W+',' ', f.read()).replace('\n', '')
    return data

############################################################
# NLP Preprocessing
############################################################
def strip_accents(data):
    data = unicodedata.normalize('NFKD', data).encode('ASCII', 'ignore').decode('utf-8')
    return data

def lemmatise_spacy(data, language_short, file_path):
    models_dict =  {
        'it': 'it_core_news_sm',
        'es': 'es_core_news_sm',
        'ja': 'ja_core_news_sm',
        'pl': 'pl_core_news_sm',
        'ge': 'de_core_news_sm',
        'en': 'en_core_web_sm'
    }
    model_str = models_dict[language_short]
    nlp = spacy.load(model_str)

    data = strip_accents(data)
    doc = nlp(data)
    lemmatised = pd.DataFrame()
    with open(file_path[:-4]+'.lemma.spacy.txt', 'w') as f:
        f.write("%s,%s,%s,%s,%s,%s\n" % ("token", "pos", "dep", "lemma", "ent_iob", "ent_type") )
        for token in doc:
            remove_types = ['PUNCT', 'NUM','X','DET','SPACE']
            remove_det = ['det']
            lemma = strip_accents(token.lemma_)
            if token.pos_ not in remove_types and token.dep_ not in remove_det:
                lemmatised = lemmatised.append(
                    {'word':lemma, 'pos':token.pos_}, 
                    ignore_index=True
                )
            f.write("%s,%s,%s,%s,%s,%s\n" % (token.text, token.pos_, token.dep_, lemma, 
                                       token.ent_iob_, token.ent_type_) )
    return lemmatised

# def remove_stop_words(word_list, language):
#     raise Exception("Not Implemented")
    # stop_words = set(['a']
    #     # stopwords.words(language)
    #     )  # load stopwords
    # return remove_known(word_list, stop_words)

def remove_known(word_list, words_remove):
    word_list = [w for w in word_list if w not in words_remove]
    return word_list


############################################################
# Anki
############################################################
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

######################################## 
# Analysis and statistics
######################################## 

# def get_frequent_words(word_list, language, min_count=2):
#     # if remove_stopwords is True:
#         # word_list = remove_stop_words(word_list, language=language)
#     new_data = Counter(word_list)
#     for key, count in dropwhile(lambda key_count: key_count[1] >= min_count, new_data.most_common()):
#         del new_data[key]
#     df = pd.DataFrame.from_dict(new_data.most_common())
#     df.columns = ['word', 'occurrences']    
#     return df

def get_df_to_learn(df, min_frequency = 2):
    total_len = len(df)
    # Remove the proper names
    df = df[df.pos != 'PROPN'].sort_values('occurrences',ascending=False)
    
    df_unknown = df[(df.is_known == 0) & (df.is_anki == 0) ]
    df_known = df[(df.is_known == 1) | (df.is_anki == 1) ]
    df_to_learn = df_unknown[df_unknown.occurrences >= min_frequency]

    total_high_freq = len(df[df.occurrences >= min_frequency])
    movie_word_count = df.occurrences.sum()
    pct_movie_known = df_known.occurrences.sum() / movie_word_count
    pct_unique_known = len(df_known) / len(df)
    pct_unique_known_highfreq = (total_high_freq - len(df_to_learn) ) / total_high_freq
    high_freq_sum = df[(df.occurrences > min_frequency) | 
                       ((df.is_known == 1) | (df.is_anki == 1))
                    ].occurrences.sum()
    print(high_freq_sum)
    print(60*'-')
    print("Words - Unknown:{} Known:{} TotNotNames:{} Total:{}".format(len(df_unknown), len(df_known), len(df), total_len ))
    print("% of movie known:          {:.0%} / {:4d}".format(pct_movie_known, movie_word_count))
    print("% of words known:          {:.0%} / {:4d}".format(pct_unique_known, len(df) ))
    
    print("% of words[freq>={}] known: {:.0%} / {:4d}".format( min_frequency,
        pct_unique_known_highfreq,
        total_high_freq
    ))
    print("% of movie if known highfreq: {:.0%}".format(high_freq_sum / movie_word_count) )

    print(60*'-')
    print(df_unknown.groupby('occurrences').size())
    print(60*'-')
    
    return df_to_learn

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

def get_combined_df(lemmatised, anki_df, manual_known):    
    # Combine to get the word counts
    df = lemmatised.groupby(['word','pos']).size().rename('occurrences').reset_index()
    df = (df
        .merge(anki_df, on='word',how='left')
        .merge(manual_known, on='word', how='left')
        .fillna(0)
    )
    
LANG_TRANSLATE_MODEL_PATH = './models/lid.176.ftz'
known = ['nella','i','d','qui','po','dell','c','questi','tv']
anki_csv_path = 'anki.lemma.csv'

################################################################################
############################################
# Arguments & Config
############################################

def load_config():
    cfg = configparser.ConfigParser()
    cfg.read('config.ini')
    return cfg

def parse_args(default_anki_path, default_card_deck):
    parser = argparse.ArgumentParser(description='Processes the SRT and Anki.')
    parser.add_argument('srt_path', help='srt_path')
    parser.add_argument('--anki_path', help='anki_path', default=default_anki_path)
    parser.add_argument('--card_deck', help='card_deck', default=default_card_deck)
    parser.add_argument('--srt_encoding', help='srt_encoding')
    parser.add_argument('--srt_lang', help='srt lang [2 chars]...[en,it]')
    
    args = parser.parse_args()
    
    return args

def main(args):
    cfg = load_config()
    args = parse_args(cfg['anki']['anki_path'], cfg['anki']['card_deck'])
    
    card_deck = args.card_deck
    anki_path = args.anki_path 
    srt_path = args.srt_path
    language_short = args.srt_lang
    srt_encoding = args.srt_encoding
    
    srt_path_noext = srt_path[:-4]

    if language_short is None:
        language_short = detect_file_language(srt_path)
    language = languages.get(alpha_2=language_short).name.lower()
    
    try:
        anki_df = pd.read_csv(anki_csv_path)
    except Exception as e:
        anki = parse_anki(load_anki(anki_path, card_deck))
        anki_together  = ' '.join(anki)
        anki_df = lemmatise_spacy(anki_together, language_short, 'anki.srt')[['word']]
        anki_df = anki_df.append(pd.DataFrame({'word':anki})).drop_duplicates()
        anki_df['is_anki'] = 1
        anki_df.to_csv(anki_csv_path, index=False)
    
    manual_known = pd.DataFrame({'word':known})
    manual_known['is_known'] = 1
    
    lemmatised_csv_path = srt_path_noext+'.lemma.csv'
    try:
        lemmatised = pd.read_csv(lemmatised_csv_path)
    except Exception as e:
        new_file_name = srt2text(srt_path, encoding=srt_encoding)
        data = load_txt(new_file_name)
        lemmatised = lemmatise_spacy(data, language_short, srt_path)
        lemmatised.to_csv(lemmatised_csv_path, index=False)

    df = get_combined_df(lemmatised, anki_df, manual_known)

    csv_path_all = srt_path_noext + '.csv'
    df.to_csv(csv_path_all, index = False)

    df_to_learn = get_df_to_learn(df).reset_index(drop=True)
    csv_path_unknwon = srt_path_noext + '.unknown.csv'
    df_to_learn.to_csv(csv_path_unknwon, index = False)
    print(df_to_learn)

    generate_deck(df_to_learn, srt_path_noext)

if __name__ == '__main__':
    main(sys.argv)