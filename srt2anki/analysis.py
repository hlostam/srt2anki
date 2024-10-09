import unicodedata
import re

import pandas as pd
import spacy

known = ['nella','i','d','qui','po','dell','c','questi','tv',"anch'","i'"]

def get_manual_known_df():
        manual_known = pd.DataFrame({'word':known})
        manual_known['is_known'] = 1
        return manual_known

############################################################
# NLP Preprocessing
############################################################
def strip_accents(data):
    data = unicodedata.normalize('NFKD', data).encode('ASCII','ignore').decode('utf-8')
    return data

def lemmatise_spacy(data, language_short):
    models_dict =  {
        'it': 'it_core_news_sm',
        'es': 'es_core_news_sm',
        'ja': 'ja_core_news_sm',
        'pl': 'pl_core_news_sm',
        'ge': 'de_core_news_sm',
        'en': 'en_core_web_sm'
    }
    model_str = models_dict[language_short]
    try:
        nlp = spacy.load(model_str)
    except Exception as e:
        raise Exception(f"This language: {language_short} is not supported - the web version supports only IT, ES, DE.")
    data = strip_accents(data)
    doc = nlp(data)
    lemmatised = pd.DataFrame()
    # with open(file_name[:-4]+'.lemma.spacy.txt', 'w') as f:
    # f.write("%s,%s,%s,%s,%s,%s\n" % ("token", "pos", "dep", "lemma", "ent_iob", "ent_type") )
    for token in doc:
        remove_types = ['PUNCT', 'NUM','X','DET','SPACE']
        remove_det = ['det']
        lemma = strip_accents(token.lemma_)
        if token.pos_ not in remove_types and token.dep_ not in remove_det:
            lemmatised = lemmatised.append(
                {'word':lemma, 'pos':token.pos_}, 
                ignore_index=True
            )
    # f.write("%s,%s,%s,%s,%s,%s\n" % (token.text, token.pos_, token.dep_, lemma, 
                                    # token.ent_iob_, token.ent_type_) )
    
    # Some manual fixes
    if language_short == 'it':
        for a,b in [('perchA','perche'),('piA1','piu')]:
            lemmatised['word'] = lemmatised['word'].map(lambda x : x.replace(a,b))
        
    return lemmatised
    
def remove_known(word_list, words_remove):
    word_list = [w for w in word_list if w not in words_remove]
    return word_list

# Statistics / final DF preprocessing
def get_combined_df(df_srt, df_anki, df_manual_known):    
    # Combine to get the word counts
    df = df_srt.groupby(['word','pos']).size().rename('occurrences').reset_index()
    df = (df
        .merge(df_anki, on='word',how='left')
        .merge(df_manual_known, on='word', how='left')
        .fillna(0)
    )
    return df

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
    summary_str = ""
    summary_str += 60*'-'
    summary_str += "\nWords - Unknown:{} Known:{} TotNotNames:{} Total:{} \n".format(
        len(df_unknown), len(df_known), len(df), total_len )
    summary_str += "% of movie known:          {:.0%} / {:4d}\n".format(
        pct_movie_known, movie_word_count)
    summary_str +="% of words known:          {:.0%} / {:4d}\n".format(pct_unique_known, len(df) )
    
    summary_str += "% of words[frequency >= {}] known: {:.0%} / {:4d}\n".format( min_frequency,
        pct_unique_known_highfreq,
        total_high_freq
    )
    summary_str += 60*'-'
    summary_str += "\n"
    summary_str += """
    You already know {} out of {} words in this movie, i.e. {:.0%}. There are {} words
     that appear at least {}x in the movie. Out of them, you know {} words, 
     i.e. {:.0%}. 
    
    If you learn the remaining {} words that appear in the movie at least {}x, you will 
    understand {:.0%} of the whole movie.\n
    """.format(
        len(df_known), len(df), pct_movie_known,
        total_high_freq, min_frequency, (total_high_freq - len(df_to_learn)), pct_unique_known_highfreq, 
        len(df_to_learn), min_frequency,
        high_freq_sum / movie_word_count) 

    # summary_str += 60*'-'
    # summary_str += 60*'-'df_unknown.groupby('occurrences').size()
    
    
    return df_to_learn.reset_index(drop=True), summary_str