import streamlit as st
import pandas as pd
import chardet
import io
import re
import os

def detect_encoding(file_content):
    result = chardet.detect(file_content)
    encoding = result['encoding']
    return encoding

def process_file(input_file, delimiter, columns_to_remove_spaces, default_value="NA"):
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

        # Check for empty columns and drop them
        original_df = original_df.dropna(axis=1, how='all')

        # Convert all columns to string type
        original_df = original_df.astype(str)

        # Create a copy of the DataFrame for cleaning to preserve the original data
        df = original_df.copy()

        # Cleaning operations
        space_removal_counts = 0
        for col_idx in columns_to_remove_spaces:
            col = df.columns[col_idx]
            # Remove spaces from the selected columns
            df[col] = df[col].str.replace('\s+', '', regex=True)
            # Count spaces removed from the end of each value
            space_removal_counts += (original_df[col].str.len() - original_df[col].str.rstrip().str.len()).sum()
            # Remove foreign characters from the selected columns
            df[col] = df[col].apply(remove_foreign_characters)
            # Adjust values according to specifications
            df[col] = df[col].apply(adjust_values)

        df.fillna(default_value, inplace=True)

        return original_df, df, space_removal_counts  # Return both the original and cleaned DataFrame
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")
        return None, None, None

def remove_foreign_characters(value):
    if isinstance(value, str):
        # Remove foreign characters
        return re.sub(r'[^a-zA-Z0-9,.@äöüÄÖÜß\s]+', '', value)
    return value

def adjust_values(value):
    if isinstance(value, str):
        # Remove 'AM' from the end and convert 'PM' to 'p'
        value = value.replace('AM', 'a').replace('PM', 'p')
        # Remove everything after ':' and take out ':' if it's followed by 'AM' or 'PM'
        value = re.sub(r'(\d+):(\d+)\s?(AM|PM)?', r'\1\3', value)
        return value
    return value

# Streamlit UI setup
st.title("CSV- und TXT-Datei bereinigen und analysieren")

input_file = st.file_uploader("Laden Sie Ihre CSV- oder TXT-Datei hoch:", type=["csv", "txt"])
delimiter = st.text_input("Geben Sie das Trennzeichen Ihrer Datei ein:", ";")
default_value = st.text_input("Standardwert für fehlende Daten:", "NA")

if input_file and delimiter:
    original_df = pd.read_csv(input_file, sep=delimiter, header=None)

    # Select columns to remove spaces
    remove_spaces_columns = st.multiselect("Wählen Sie die Spalten aus, aus denen Sie alle Leerzeichen entfernen möchten:", range(len(original_df.columns)), format_func=lambda x: f"Spalte {x+1}")

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
        st.write(f"Anzahl der entfernten Leerzeichen: {space_removal_counts}")

        # Download-Link für bereinigte Daten
        output_file_name = os.path.splitext(os.path.basename(input_file.name))[0] + "_bereinigt.csv"
        cleaned_csv = cleaned_df.to_csv(index=False, header=False, sep=delimiter)  # No header and using specified delimiter
        st.download_button(label="Bereinigte Daten herunterladen", data=cleaned_csv, file_name=output_file_name, mime="text/csv")

else:
    st.error("Bitte laden Sie eine CSV- oder TXT-Datei hoch und geben Sie das Trennzeichen an.")
