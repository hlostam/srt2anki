import sys
import os
import streamlit as st
import io
import base64
from pathlib import Path

import pandas as pd
import numpy as np
# import cchardet as chardet
from charset_normalizer import detect

from srt2anki import anki, analysis, srt

def read_txt_file_upload(file, encoding=None):
    msg = file.read()
    if encoding is None:
        encoding = detect(msg)['encoding']
    text = str(msg, encoding)
    return text

def get_binary_file_downloader_html(bin_file, file_label='File'):
    """From:https://blog.jcharistech.com/2020/11/08/working-with-file-uploads-in-streamlit-python/"""
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">Download {file_label}</a>'
    return href

def get_table_download_link_csv(df, name, file_label='File'):
    csv = df.to_csv(index=False).encode()
    b64 = base64.b64encode(csv).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{name}.csv" target="_blank">Download {file_label}</a>'
    return href


def main():
    # st.set_option("deprecation.showPyplotGlobalUse", False)
    st.sidebar.title("srt2anki")
    anki_file_buf = st.sidebar.file_uploader("Upload apkg", type=["apkg"], key='apkg')
    srt_file_buf = st.sidebar.file_uploader("Upload srt", type=["srt"], key='srt')
    title_left, space, title_right = st.columns(
    (3.5, .2, 1,))
    
    title_left.header("Watching a foreign language movie with Anki and Subtitles analysis")
    title_right.subheader(
    'Created by [Martin Hlosta](https://www.linkedin.com/in/mhlosta/)')
    
    st.markdown("""Upload both the subtitles and Anki file in the left menu, the analysis will start automatically after the upload. You can also read my [Medium article about this project](https://medium.com/@hlostak/watching-a-foreign-language-movie-with-anki-and-subtitles-analysis-ca1a538496cb). I would be very grateful for any feedback, either under the Medium article or on [Twitter](https://twitter.com/mhlosta/status/1422836948956323843).""")

    if anki_file_buf is not None and srt_file_buf is not None:
        
        with st.spinner('Processing SRT file'):
            srt_filepath = srt_file_buf.name
            srt_path_noext = srt_filepath[:-4]

            text = read_txt_file_upload(srt_file_buf)
            
            @st.cache_data()
            def cache_srt(text):
                data = srt.srt2text(text)
                language_short = srt.detect_text_language(data)
                # st.write("Language Short", language_short)
                srt_df = analysis.lemmatise_spacy(data, language_short)
                return srt_df, language_short
            srt_df, language_short = cache_srt(text)

        with st.spinner('Processing Anki file'):
            anki_list = anki.load_apkg(anki_file_buf, language_short)
            @st.cache_data()
            def cache_anki(anki_list, language_short):
                anki_df = anki.get_anki_df(None, language_short, anki=anki_list)
                return anki_df
            anki_df = cache_anki(anki_list, language_short)
        with st.spinner('Combining files'):
            manual_known_df =  analysis.get_manual_known_df()    
            df = analysis.get_combined_df(srt_df, anki_df, manual_known_df)
            df_to_learn, summary_string = analysis.get_df_to_learn(df)
        
        st.text(summary_string)
        st.write(df_to_learn)

        file_path = anki.generate_deck(df_to_learn, srt_path_noext)
        st.markdown(get_binary_file_downloader_html(file_path, 'Anki Package [.apkg] - only unknown'), unsafe_allow_html=True)
        st.markdown(get_table_download_link_csv(df_to_learn, srt_path_noext, '.csv - only unknown'), unsafe_allow_html=True)
        st.markdown(get_table_download_link_csv(df_to_learn, srt_path_noext, '.csv - all words'), unsafe_allow_html=True)
        

if __name__ == "__main__":
    main()

