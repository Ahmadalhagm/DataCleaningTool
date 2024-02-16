import streamlit as st
import pandas as pd
import numpy as np
import chardet
import io
import re
import os
import csv

def detect_encoding(file_content):
    result = chardet.detect(file_content)
    encoding = result['encoding']
    return encoding, file_content

def remove_foreign_characters(value):
    pattern = re.compile(r'[^\w\s.,;@#\-_äöüÄÖÜß&]+')
    removed_chars = pattern.findall(value)
    new_value = pattern.sub('', value)
    return new_value, removed_chars

def process_file(input_file, delimiter, remove_spaces_columns, merge_columns, merge_separator, remove_empty_or_space_columns, compare_columns, use_column_names):
    content = input_file.getvalue()
    encoding, content = detect_encoding(content)
    try:
        decoded_content = content.decode(encoding)
        if use_column_names:
            original_df = pd.read_csv(io.StringIO(decoded_content), sep=delimiter)
        else:
            original_df = pd.read_csv(io.StringIO(decoded_content), sep=delimiter, header=None)

        if remove_empty_or_space_columns:
            original_df.replace('', pd.NA, inplace=True)
            original_df.dropna(axis=1, how='all', inplace=True)
            original_df.replace(pd.NA, '', inplace=True)

        original_df = original_df.astype(str)
        df = original_df.copy()

        if merge_columns:
            merged_column_name = df.columns[min(merge_columns)]
            df[merged_column_name] = df[merge_columns].astype(str).apply(lambda x: merge_separator.join(x), axis=1)
            df.drop(columns=[df.columns[i] for i in merge_columns if i != min(merge_columns)], inplace=True)

        space_removal_counts = {}
        foreign_characters_removed = {}
        total_foreign_characters_removed = set()

        for col in df.columns:
            original_col = df[col].copy()
            if col in remove_spaces_columns or 'All Columns' in remove_spaces_columns:
                df[col] = df[col].str.replace('\s+', '', regex=True)
                space_removal_counts[col] = (original_col.str.len() - df[col].str.len()).sum()

            df[col], removed_chars = zip(*df[col].apply(remove_foreign_characters))
            foreign_characters_removed[col] = ''.join(set().union(*removed_chars))
            total_foreign_characters_removed.update(foreign_characters_removed[col])

        if compare_columns:
            col1, col2 = compare_columns
            is_email_col1 = df[col1].str.contains(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            is_email_col2 = df[col2].str.contains(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            df[merged_column_name] = np.where(is_email_col1 & is_email_col2, df[merged_column_name].str.replace(merge_separator, ','), df[merged_column_name])

        df.fillna('', inplace=True)
        df.replace('nan', None, inplace=True)

        return original_df, df, space_removal_counts, foreign_characters_removed, total_foreign_characters_removed, encoding
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")
        return None, None, None, None, None, None

# Streamlit UI setup
st.title("CSV- und TXT-Datei bereinigen und analysieren")
input_file = st.file_uploader("Laden Sie Ihre CSV- oder TXT-Datei hoch:", type=["csv", "txt"])
delimiter = st.text_input("Geben Sie das Trennzeichen Ihrer Datei ein:", ";")
remove_empty_or_space_columns = st.checkbox("Spalten entfernen, wenn alle Werte Leerzeichen oder None sind")
column_options = "100"
try:
    max_columns = int(column_options)
    column_range = list(range(max_columns))
except ValueError:
    st.error("Bitte geben Sie eine gültige Zahl ein.")
remove_spaces_columns = st.multiselect("Wählen Sie die Spalten aus, aus denen Sie alle Leerzeichen entfernen möchten:", ['All Columns'] + column_range, default=[])
merge_columns_selection = st.multiselect("Wählen Sie zwei oder mehr Spalten zum Zusammenführen aus:", column_range, default=[])
merge_separator = st.text_input("Geben Sie den Trennzeichen für das Zusammenführen der Spalten ein:", ",")
compare_columns = st.multiselect("Wählen Sie zwei Spalten zum Vergleich aus:", column_range, default=[])
use_column_names = st.checkbox("Verwenden Sie die erste Zeile als Spaltennamen (falls vorhanden)")

if input_file and delimiter:
    original_df, cleaned_df, space_removal_counts, foreign_characters_removed, total_foreign_characters_removed, encoding = process_file(input_file, delimiter, remove_spaces_columns, merge_columns_selection, merge_separator, remove_empty_or_space_columns, compare_columns, use_column_names)
    if original_df is not None and cleaned_df is not None:
        st.write("### Vorschau der Originaldaten")
        st.dataframe(original_df.head())
        st.write("### Vorschau der bereinigten Daten")
        st.dataframe(cleaned_df.head())
        
        with st.expander("Analyse", expanded=False):
            st.write("#### Datenbereinigungsanalyse")
            st.write(f"Dateikodierung: {encoding}")
            st.write(f"Ursprüngliche Zeilen: {len(original_df)}, Ursprüngliche Spalten: {original_df.shape[1]}")
            st.write(f"Bereinigte Zeilen: {len(cleaned_df)}, Bereinigte Spalten: {cleaned_df.shape[1]}")
            for col, count in space_removal_counts.items():
                st.write(f"Leerzeichen entfernt in Spalte '{col}': {count}")
            st.write(f"Entfernte fremde Zeichen: {', '.join(total_foreign_characters_removed)}")
            for col, chars in foreign_characters_removed.items():
                if chars:
                    st.write(f"Spalte '{col}' entfernte Zeichen: {chars}")
            
            # Statistical Summary for numerical data
            if not cleaned_df.select_dtypes(include=np.number).empty:
                st.write("### Erweiterte statistische Analyse für numerische Daten")
                desc, skewness, kurt, outliers = statistical_analysis(cleaned_df.select_dtypes(include=[np.number]))
                st.dataframe(desc)
                st.write("### Schiefe (Skewness)")
                st.dataframe(skewness)
                st.write("### Wölbung (Kurtosis)")
                st.dataframe(kurt)
                st.write("### Ausreißer (Outliers)")
                st.dataframe(outliers)

        cleaned_csv_buffer = io.StringIO()
        cleaned_df.to_csv(cleaned_csv_buffer, index=False, header=False, sep=delimiter, quoting=csv.QUOTE_NONNUMERIC, encoding='utf-8-sig')
        cleaned_csv_data = cleaned_csv_buffer.getvalue()
        cleaned_csv_buffer.seek(0)
        st.download_button("Bereinigte Daten herunterladen", data=cleaned_csv_data.encode('utf-8-sig'), file_name=os.path.splitext(input_file.name)[0] + "_bereinigt.csv", mime="text/csv")
