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

def process_file(input_file, delimiter, remove_spaces_columns, default_value="NA"):
    content = input_file.getvalue()
    encoding = detect_encoding(content)

    try:
        # Decode the content using the detected encoding
        decoded_content = content.decode(encoding)

        # Load the original data
        original_df = pd.read_csv(io.StringIO(decoded_content), sep=delimiter, header=None)

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

def remove_foreign_characters(value):
    if isinstance(value, str):
        # Remove foreign characters except spaces and German umlauts
        return re.sub(r'[^\w\s.,;@\-_äöüÄÖÜß]+', '', value)
    return value

def replace_am_and_remove_zeros(value):
    if isinstance(value, str):
        # Replace "AM" with "A"
        value = value.replace("AM", "A")
        # Remove two zeros if found
        value = re.sub(r'(\d+)00(?=\s*A$)', r'\1', value)
        return value.strip()  # Remove leading and trailing whitespaces
    return value

# Streamlit UI setup
st.title("CSV- und TXT-Datei bereinigen und analysieren")

input_file = st.file_uploader("Laden Sie Ihre CSV- oder TXT-Datei hoch:", type=["csv", "txt"])
delimiter = st.text_input("Geben Sie das Trennzeichen Ihrer Datei ein:", ";")
default_value = st.text_input("Standardwert für fehlende Daten:", "NA")

if input_file and delimiter:
    original_df = pd.read_csv(input_file, sep=delimiter, header=None)

    if original_df is not None:
        st.write("### Vorschau der Originaldaten")
        st.dataframe(original_df.head())

        # Multiselect widget to choose columns for removing spaces
        remove_spaces_columns = st.multiselect("Wählen Sie die Spalten aus, aus denen Sie alle Leerzeichen entfernen möchten:",
                                               original_df.columns)

        original_df, cleaned_df, space_removal_counts = process_file(input_file, delimiter, remove_spaces_columns, default_value)

        if original_df is not None and cleaned_df is not None:
            st.write("### Vorschau der bereinigten Daten")
            st.dataframe(cleaned_df.head())

            st.write("### Bereinigungszusammenfassung")

            # Display counts of removed spaces for each selected column
            for col, count in space_removal_counts.items():
                st.write(f"Anzahl der entfernten Leerzeichen in Spalte '{col}': {count}")

            st.write(f"Ursprüngliche Zeilen: {len(original_df)}, Bereinigte Zeilen: {len(cleaned_df)}")

            # Analyse der Leerzeichenentfernung
            st.write("### Analyse der Leerzeichenentfernung")
            total_space_removal_counts = sum(space_removal_counts.values())
            st.write(f"Gesamtanzahl der entfernten Leerzeichen: {total_space_removal_counts}")

            # Download-Link für bereinigte Daten
            cleaned_excel_path = os.path.splitext(input_file.name)[0] + "_bereinigt.xlsx"
            cleaned_df.to_excel(cleaned_excel_path, index=False, header=False, engine='openpyxl', encoding='utf-8-sig')
            st.download_button(label="Bereinigte Daten herunterladen", data=open(cleaned_excel_path, 'rb').read(),
                               file_name=cleaned_excel_path, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

else:
    st.error("Bitte laden Sie eine CSV- oder TXT-Datei hoch und geben Sie das Trennzeichen an.")
