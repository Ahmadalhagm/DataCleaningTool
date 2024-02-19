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
    return new_value, ''.join(set(removed_chars))

def process_file(input_file, delimiter, remove_spaces_columns, normal_merge_columns, normal_merge_separator, merge_columns, merge_separator, remove_empty_or_space_columns, correct_misinterpretation):
    content = input_file.getvalue()
    encoding, content = detect_encoding(content)
    try:
        decoded_content = content.decode(encoding)
        df = pd.read_csv(io.StringIO(decoded_content), sep=delimiter, header=None, dtype=str)

        if remove_empty_or_space_columns:
            df.replace('', pd.NA, inplace=True)
            df.dropna(axis=1, how='all', inplace=True)
            df.replace(pd.NA, '', inplace=True)

        # Normal Merging of two columns
        if normal_merge_columns and len(normal_merge_columns) == 2:
            col1, col2 = [int(c) - 1 for c in normal_merge_columns]  # Adjusted for 0-based index
            df[f'Merged_Normal_{col1}_{col2}'] = df.iloc[:, col1] + normal_merge_separator + df.iloc[:, col2]
            df.drop(columns=[df.columns[col1], df.columns[col2]], inplace=True)

        # Handle space and foreign character removal here, as per previous logic

        # Conditional Merging based on "Korrekte Fehlinterpretation"
        if correct_misinterpretation and merge_columns and len(merge_columns) >= 2:
            # This example assumes merge_columns is a list of columns selected for merging.
            merge_col_indices = [int(c) - 1 for c in merge_columns]  # Adjust if using names or other identifiers
            for index, row in df.iterrows():
                if row.iloc[-1].strip() in ('', 'None', 'nan'):
                    merged_value = merge_separator.join(row[merge_col_indices].astype(str))
                    df.at[index, merge_col_indices[0]] = merged_value
            df.drop(columns=df.columns[merge_col_indices[1:]], inplace=True)

        space_removal_counts = {}  # Implement space removal logic if required
        foreign_characters_removed = {}  # Implement foreign character removal logic if required
        total_foreign_characters_removed = set()  # Implement tracking of removed foreign characters if required

        return df, encoding, space_removal_counts, foreign_characters_removed, total_foreign_characters_removed
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")
        return None, None, None, None, None

st.title("CSV- und TXT-Datei bereinigen und analysieren")

input_file = st.file_uploader("Laden Sie Ihre CSV- oder TXT-Datei hoch:", type=["csv", "txt"])
delimiter = st.text_input("Geben Sie das Trennzeichen Ihrer Datei ein:", ";")
remove_empty_or_space_columns = st.checkbox("Spalten entfernen, wenn alle Werte Leerzeichen oder None sind")
correct_misinterpretation = st.checkbox("Korrekte Fehlinterpretationen")

# Normal Merge UI Components
normal_merge_columns_selection = st.text_input("Normal Merge Columns (e.g., '1,2'):", "")
normal_merge_separator = st.text_input("Separator for normal merging:", ",")

# Conditional Merge UI Components
merge_columns_selection = st.text_input("Conditional Merge Columns (e.g., '3,4') for 'Korrekte Fehlinterpretation':", "")
merge_separator = st.text_input("Separator for conditional merging:", ",")

# Convert user input for column selection into list format
normal_merge_columns = [x.strip() for x in normal_merge_columns_selection.split(',') if x.strip().isdigit()]
merge_columns = [x.strip() for x in merge_columns_selection.split(',') if x.strip().isdigit()]

if input_file and delimiter:
    processed_df, encoding, space_removal_counts, foreign_characters_removed, total_foreign_characters_removed = process_file(
        input_file, delimiter, [], normal_merge_columns, normal_merge_separator, merge_columns, merge_separator, remove_empty_or_space_columns, correct_misinterpretation
    )
    if processed_df is not None:
        st.write("### Vorschau der bereinigten Daten")
        st.dataframe(processed_df)

        # Download cleaned data
        cleaned_csv_buffer = io.StringIO()
        processed_df.to_csv(cleaned_csv_buffer, index=False, sep=delimiter, quoting=csv.QUOTE_NONNUMERIC, encoding='utf-8-sig')
        cleaned_csv_data = cleaned_csv_buffer.getvalue()
        st.download_button("Bereinigte Daten herunterladen", data=cleaned_csv_data.encode('utf-8-sig'), file_name="bereinigte_daten.csv", mime="text/csv")
