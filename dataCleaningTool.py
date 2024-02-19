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

def process_file(input_file, delimiter, remove_spaces_columns, merge_columns_selection, merge_separator, remove_empty_or_space_columns, correct_misinterpretation):
    content = input_file.getvalue()
    encoding_before, content = detect_encoding(content)
    file_size_before = len(content)
    try:
        decoded_content = content.decode(encoding_before)
        df = pd.read_csv(io.StringIO(decoded_content), sep=delimiter, header=None, dtype=str)
        original_rows, original_columns = df.shape

        # Initialize cleaning summary
        cleaning_summary = {
            'spaces_removed': 0,
            'foreign_characters_removed': set(),
            'empty_columns_removed': 0,
            'rows_with_nan_at_end': 0,
            'encoding_before': encoding_before,
            'file_size_before_kb': file_size_before / 1024,
            'encoding_after': encoding_before,  # This will not change
        }

        if remove_empty_or_space_columns:
            empty_columns_before = df.shape[1]
            df.replace('', np.nan, inplace=True)
            df.dropna(axis=1, how='all', inplace=True)
            df.fillna('', inplace=True)
            empty_columns_after = df.shape[1]
            cleaning_summary['empty_columns_removed'] = empty_columns_before - empty_columns_after

        for col in df.columns:
            if 'All Columns' in remove_spaces_columns or col in remove_spaces_columns:
                space_count_before = df[col].apply(lambda x: x.count(' ')).sum()
                df[col] = df[col].str.replace('\s+', ' ', regex=True)
                space_count_after = df[col].apply(lambda x: x.count(' ')).sum()
                cleaning_summary['spaces_removed'] += (space_count_before - space_count_after)

            new_values, removed_chars = zip(*df[col].apply(remove_foreign_characters))
            df[col] = new_values
            cleaning_summary['foreign_characters_removed'].update(set().union(*removed_chars))

        cleaning_summary['rows_with_nan_at_end'] = df[df.iloc[:, -1].isna() | (df.iloc[:, -1] == '')].shape[0]

        # Merge columns based on user selection and conditions
        merge_columns = [int(x.strip()) - 1 for x in merge_columns_selection.split(',') if x.strip().isdigit()]
        if merge_columns and len(merge_columns) >= 2:
            if not correct_misinterpretation:
                df['Merged_Column'] = df.iloc[:, merge_columns[0]].astype(str) + merge_separator + df.iloc[:, merge_columns[1]].astype(str)
                df.drop(columns=df.columns[merge_columns], inplace=True)
            else:
                # Implement conditional merging logic here
                pass  # Placeholder for conditional merging logic

        file_size_after = df.memory_usage(deep=True).sum()
        cleaning_summary['file_size_after_kb'] = file_size_after / 1024
        cleaning_summary['rows_after'] = df.shape[0]
        cleaning_summary['columns_after'] = df.shape[1]

        return df, cleaning_summary
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None, None

st.title("CSV- und TXT-Datei bereinigen und analysieren")

input_file = st.file_uploader("Laden Sie Ihre CSV- oder TXT-Datei hoch:", type=["csv", "txt"])
delimiter = st.text_input("Geben Sie das Trennzeichen Ihrer Datei ein:", ";")
remove_empty_or_space_columns = st.checkbox("Spalten entfernen, wenn alle Werte Leerzeichen oder None sind")
remove_spaces_columns = st.multiselect("Wählen Sie die Spalten aus, aus denen Sie alle Leerzeichen entfernen möchten:", ['All Columns'], default=[])
merge_columns_selection = st.text_input("Geben Sie die Spaltenindizes für das Zusammenführen ein (z.B. '1,2'):", "")
merge_separator = st.text_input("Geben Sie den Trennzeichen für das Zusammenführen der Spalten ein:", ",")
correct_misinterpretation = st.checkbox("Korrekte Fehlinterpretationen")

if input_file and delimiter:
    cleaned_df, cleaning_summary = process_file(input_file, delimiter, remove_spaces_columns, merge_columns_selection, merge_separator, remove_empty_or_space_columns, correct_misinterpretation)
    if cleaned_df is not None:
        st.write("### Cleaning Summary")
        for key, value in cleaning_summary.items():
            st.write(f"{key.replace('_', ' ').capitalize()}: {value}")

        # Download Button for Cleaned Data
        cleaned_csv = cleaned_df.to_csv(index=False).encode('utf-8')
        st.download_button(label="Download Cleaned Data",
                           data=cleaned_csv,
                           file_name=f"cleaned_{input_file.name}",
                           mime="text/csv")
