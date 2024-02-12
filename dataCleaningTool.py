import streamlit as st
import pandas as pd
import chardet
import io
import re

def detect_encoding(file_content):
    result = chardet.detect(file_content)
    encoding = result['encoding']
    return encoding

def process_file(input_file, delimiter, name_column, ibahn_columns, default_value="NA"):
    content = input_file.getvalue()
    encoding = detect_encoding(content)

    try:
        # Load the original data
        if input_file.name.endswith('.csv'):
            original_df = pd.read_csv(io.BytesIO(content), sep=delimiter, encoding=encoding)
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
        for col in df.columns:
            if col in ibahn_columns:
                # Remove spaces from values in IBAN columns
                df[col] = df[col].str.replace(" ", "")
            elif col == name_column:
                # Replace ';' with space in the name column
                df[col] = df[col].str.replace(";", " ")
            else:
                # Merge values separated by ';'
                df[col] = df[col].str.replace(f'{delimiter}\s*', f'{delimiter}', regex=True)

                # Remove characters that are not letters, numbers, periods, commas, or spaces
                df[col] = df[col].str.replace('[^a-zA-Z0-9.,;@ ]', '', regex=True)

                # Remove trailing spaces without affecting spaces within words
                df[col] = df[col].str.rstrip()

                # Count spaces removed from the end of each value
                space_removal_counts += (original_df[col].str.len() - original_df[col].str.rstrip().str.len()).sum()

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
    ibahn_columns = []
    for col in original_df.columns:
        is_ibahn = st.checkbox(f"Spalte '{col}' enthält IBANs")
        if is_ibahn:
            ibahn_columns.append(col)

    name_column = st.selectbox("Wählen Sie die Name-Spalte aus:", original_df.columns)
    st.write(f"Sie haben '{name_column}' als Name-Spalte ausgewählt.")

    original_df, cleaned_df, space_removal_counts = process_file(input_file, delimiter, name_column, ibahn_columns, default_value)
    
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
        cleaned_csv = cleaned_df.to_csv(index=False)
        st.download_button(label="Bereinigte Daten herunterladen", data=cleaned_csv, file_name="bereinigte_daten.csv", mime="text/csv")

else:
    st.error("Bitte laden Sie eine CSV- oder TXT-Datei hoch und geben Sie das Trennzeichen an.")
