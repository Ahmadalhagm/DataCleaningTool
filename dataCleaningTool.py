import streamlit as st
import pandas as pd
import chardet
import io
import re

def detect_encoding(file_content):
    result = chardet.detect(file_content)
    encoding = result['encoding']
    return encoding

def remove_foreign_characters(value):
    if isinstance(value, str):
        return re.sub(r'[^\w.,;@ -]', '', value)
    return value

def replace_am_and_remove_zeros(value):
    if isinstance(value, str):
        value = re.sub(r'\b(\d+):00 AM\b', r'\1 A', value)
        value = re.sub(r'AM\b', 'A', value)
        value = re.sub(r'\b0{2}', '', value)  # Remove two zeros
        return value
    return value

def process_file(input_file, delimiter, remove_spaces_columns, default_value="NA"):
    content = input_file.getvalue()
    encoding = detect_encoding(content)

    try:
        # Load the original data
        if input_file.name.endswith('.csv'):
            original_df = pd.read_csv(io.BytesIO(content), sep=delimiter, encoding=encoding, header=None)
        elif input_file.name.endswith('.txt'):
            original_df = pd.read_csv(io.BytesIO(content), sep=delimiter, encoding=encoding, header=None)
        else:
            st.error("Nur .csv- und .txt-Dateien werden unterstützt.")
            return None, None, None

        # Replace NaN values with empty strings
        original_df.fillna('', inplace=True)

        # Check for empty columns and drop them
        original_df = original_df.dropna(axis=1, how='all')

        # Convert all columns to string type
        original_df = original_df.astype(str)

        # Create a copy of the DataFrame for cleaning to preserve the original data
        df = original_df.copy()

        # Cleaning operations
        space_removal_counts = {}
        for col in df.columns:
            if col in remove_spaces_columns:
                # Remove spaces from selected columns
                df[col] = df[col].str.replace('\s+', '', regex=True)
                # Count spaces removed from the end of each value
                space_removal_counts[col] = (original_df[col].str.len() - original_df[col].str.rstrip().str.len()).sum()

            # Remove foreign characters from all values in the column without removing spaces
            df[col] = df[col].apply(remove_foreign_characters)
            # Replace "AM" with "A" and remove two zeros if found
            df[col] = df[col].apply(replace_am_and_remove_zeros)

        df.fillna(default_value, inplace=True)

        return original_df, df, space_removal_counts  # Return both the original and cleaned DataFrame
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")
        return None, None, None

# Streamlit UI setup
st.title("CSV- und TXT-Datei bereinigen und analysieren")

input_file = st.file_uploader("Laden Sie Ihre CSV- oder TXT-Datei hoch:", type=["csv", "txt"])
delimiter = st.text_input("Geben Sie das Trennzeichen Ihrer Datei ein:", ";")
default_value = st.text_input("Standardwert für fehlende Daten:", "NA")

if input_file and delimiter:
    original_df = pd.read_csv(input_file, sep=delimiter)

    # Get column names as numbers for selector
    column_numbers = [str(i) for i in range(len(original_df.columns))]

    # Select columns to remove spaces
    remove_spaces_columns = st.multiselect("Wählen Sie die Spalten aus, aus denen Sie Leerzeichen entfernen möchten:", column_numbers)
    st.write(f"Sie haben die folgenden Spalten ausgewählt, um Leerzeichen zu entfernen: {remove_spaces_columns}")

    original_df, cleaned_df, space_removal_counts = process_file(input_file, delimiter, remove_spaces_columns, default_value)
    
    if original_df is not None and cleaned_df is not None:
        st.write("### Originaldaten Vorschau")
        st.dataframe(original_df.head())

        st.write("### Bereinigte Daten Vorschau")
        st.dataframe(cleaned_df.head())

        st.write("### Bereinigungszusammenfassung")
        st.write(f"Ursprüngliche Zeilen: {len(original_df)}, Bereinigte Zeilen: {len(cleaned_df)}")

        # Analyse der Leerzeichenentfernung
        st.write("### Analyse der Leerzeichenentfernung")
        for col, count in space_removal_counts.items():
            st.write(f"Anzahl der entfernten Leerzeichen in Spalte '{col}': {count}")

        # Download-Link für bereinigte Daten
        cleaned_csv = cleaned_df.to_csv(index=False, header=False, sep=delimiter)  # No header and using specified delimiter
        st.download_button(label="Bereinigte Daten herunterladen", data=cleaned_csv, file_name=input_file.name, mime="text/csv")

else:
    st.error("Bitte laden Sie eine CSV- oder TXT-Datei hoch und geben Sie das Trennzeichen an.")
