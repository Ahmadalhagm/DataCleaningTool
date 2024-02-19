import streamlit as st
import pandas as pd
import numpy as np
import chardet
import io
import csv

def detect_encoding(file_content):
    result = chardet.detect(file_content)
    encoding = result['encoding']
    return encoding, file_content

def remove_foreign_characters(value):
    if pd.isna(value):
        return value, ''
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

        cleaning_summary = {
            'spaces_removed': 0,
            'foreign_characters_removed': set(),
            'empty_columns_removed': original_columns - df.dropna(axis=1, how='all').shape[1],
            'encoding_before': encoding_before,
            'file_size_before_kb': file_size_before / 1024,
            'rows_with_nan_at_end': sum(df.iloc[:, -1].isna() | df.iloc[:, -1].apply(lambda x: x.strip() in ('', 'None', 'nan'))),
        }

        # Convert columns for space removal to integers
        remove_spaces_columns = [int(col) - 1 for col in remove_spaces_columns if col.isdigit()]

        # Remove spaces
        for col in remove_spaces_columns:
            original_len = df.iloc[:, col].str.len().sum()
            df.iloc[:, col] = df.iloc[:, col].replace(np.nan, '').replace('\s+', ' ', regex=True)
            new_len = df.iloc[:, col].str.len().sum()
            cleaning_summary['spaces_removed'] += (original_len - new_len)

        # Remove foreign characters
        for col in df.columns:
            df[col], removed_chars = zip(*df[col].apply(remove_foreign_characters))
            cleaning_summary['foreign_characters_removed'].update(removed_chars)

        # Merging columns
        merge_columns = [int(x) - 1 for x in merge_columns_selection.split(',') if x.isdigit()]
        if merge_columns and len(merge_columns) >= 2:
            col1, col2 = merge_columns[:2]
            df.iloc[:, col1] = df.iloc[:, col1].astype(str) + merge_separator + df.iloc[:, col2].astype(str)
            df.drop(columns=[col2], inplace=True)

        # Final cleaning summary updates
        file_size_after = df.memory_usage(deep=True).sum()
        cleaning_summary['file_size_after_kb'] = file_size_after / 1024
        cleaning_summary['rows_after'] = df.shape[0]
        cleaning_summary['columns_after'] = df.shape[1]

        return df, cleaning_summary
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None, None

# Streamlit UI
st.title("CSV- und TXT-Datei bereinigen und analysieren")

input_file = st.file_uploader("Laden Sie Ihre CSV- oder TXT-Datei hoch:", type=["csv", "txt"])
delimiter = st.text_input("Geben Sie das Trennzeichen Ihrer Datei ein:", ";")
remove_empty_or_space_columns = st.checkbox("Spalten entfernen, wenn alle Werte Leerzeichen oder None sind")
remove_spaces_columns = st.text_input("Geben Sie die Indizes der Spalten ein, aus denen alle Leerzeichen entfernt werden sollen (z.B. '1,2'):", "")
merge_columns_selection = st.text_input("Geben Sie die Spaltenindizes für das Zusammenführen ein (z.B. '1,2'):", "")
merge_separator = st.text_input("Geben Sie den Trennzeichen für das Zusammenführen der Spalten ein:", ",")
correct_misinterpretation = st.checkbox("Korrekte Fehlinterpretationen")

if input_file and delimiter:
    cleaned_df, cleaning_summary = process_file(input_file, delimiter, remove_spaces_columns.split(','), merge_columns_selection, merge_separator, remove_empty_or_space_columns, correct_misinterpretation)
    if cleaned_df is not None:
        st.write("### Cleaning Summary")
        for key, value in cleaning_summary.items():
            st.write(f"{key.replace('_', ' ').capitalize()}: {value}")

        # Download button for the cleaned data
        cleaned_csv = cleaned_df.to_csv(index=False).encode('utf-8')
        st.download_button(label="Download Cleaned Data",
                           data=cleaned_csv,
                           file_name=f"cleaned_{input_file.name}",
                           mime="text/csv")
