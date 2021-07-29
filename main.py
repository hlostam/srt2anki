import os, re, sys
import itertools
import logging
from pathlib import Path
from itertools import dropwhile
from collections import Counter
import argparse
import configparser

import pandas as pd
from srt2anki import anki, analysis, srt

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
    args.srt_path = str(Path(args.srt_path).absolute())
    args.anki_path = str(Path(args.anki_path).absolute())

    return args


def main(args):
    cfg = load_config()
    args = parse_args(cfg['anki']['anki_path'], cfg['anki']['card_deck'])
    
    srt_path_noext = Path(args.srt_path).stem
    
    srt_df, language_short = srt.get_srt_df_cached(args.srt_path, args.srt_encoding, 
                    language_short=args.srt_lang)
    # language = languages.get(alpha_2=language_short).name.lower()        
    
    anki_df = anki.get_anki_df(args.anki_path, language_short, args.card_deck)
    manual_known_df =  analysis.get_manual_known_df()    
    df = analysis.get_combined_df(srt_df, anki_df, manual_known_df)
    df_to_learn, summary_string = analysis.get_df_to_learn(df)
    print(summary_string)

    # All exports 
    csv_path_all = srt_path_noext + '.csv'
    df.to_csv(csv_path_all, index = False)

    csv_path_unknwon = srt_path_noext + '.unknown.csv'
    df_to_learn.to_csv(csv_path_unknwon, index = False)
    print(df_to_learn)
    deck = anki.generate_deck(df_to_learn, srt_path_noext)

if __name__ == '__main__':
    main(sys.argv)