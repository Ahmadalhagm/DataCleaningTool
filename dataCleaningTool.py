import streamlit as st
import pandas as pd
import chardet
import io
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline
from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder

def detect_encoding(file_content):
    result = chardet.detect(file_content)
    encoding = result['encoding']
    return encoding

def process_file(input_file, delimiter, default_value="NA"):
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

        # Check for unnamed columns at the end
        unnamed_columns = [col for col in original_df.columns if 'Unnamed:' in col]
        if unnamed_columns:
            for col in unnamed_columns:
                # Get the index of the unnamed column
                idx = original_df.columns.get_loc(col)

                # Check if the next column exists and contains an email
                if idx + 1 < len(original_df.columns) and original_df.iloc[:, idx + 1].str.contains('@').all():
                    # Merge email addresses from the unnamed column and the next column
                    original_df.iloc[:, idx + 1] = original_df.iloc[:, idx].astype(str) + ', ' + original_df.iloc[:, idx + 1].astype(str)
                    # Drop the unnamed column
                    original_df.drop(columns=[col], inplace=True)

        # Convert all columns to string type
        original_df = original_df.astype(str)

        # Create a copy of the DataFrame for cleaning to preserve the original data
        df = original_df.copy()

        # Cleaning operations
        space_removal_counts = 0
        for col in df.columns:
            # Merge values separated by ';'
            df[col] = df[col].apply(lambda x: re.sub(fr'{delimiter}\s*', fr'{delimiter}', x) if isinstance(x, str) else x)

            # Remove characters that are not letters, numbers, periods, commas, or spaces
            df[col] = df[col].apply(lambda x: re.sub(r'[^a-zA-Z0-9.,;@ ]', '', x) if isinstance(x, str) else x)

            # Remove trailing spaces without affecting spaces within words
            df[col] = df[col].apply(lambda x: x.rstrip() if isinstance(x, str) else x)

            # Apply ML to identify IBANs or bank account numbers
            if col != "Ibahn":
                is_ibahn = classify_ibahn(df[col])
                if is_ibahn:
                    # Remove spaces from IBANs or bank account numbers
                    df[col] = df[col].apply(lambda x: x.replace(" ", ""))
                    df.rename(columns={col: 'Ibahn'}, inplace=True)

        df.fillna(default_value, inplace=True)

        return original_df, df, space_removal_counts  # Return both the original and cleaned DataFrame
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")
        return None, None, None

def classify_ibahn(values):
    # Here you can implement your ML model to classify IBANs or bank account numbers
    # For demonstration purposes, we'll use a simple heuristic based on the length of the string
    return values.apply(lambda x: len(x) == 22)  # Assuming IBANs are 22 characters long

def character_replacement_analysis(original_df, cleaned_df):
    # Analysis of character replacements
    replaced_chars = original_df.select_dtypes(include=['object']).replace(cleaned_df)
    char_replacement_counts = (original_df != cleaned_df).sum().sum()

    return replaced_chars, char_replacement_counts

# Streamlit UI setup
st.title("CSV- und TXT-Datei bereinigen und analysieren")

input_file = st.file_uploader("Laden Sie Ihre CSV- oder TXT-Datei hoch:", type=["csv", "txt"])
delimiter = st.text_input("Geben Sie das Trennzeichen Ihrer Datei ein:", ";")
default_value = st.text_input("Standardwert für fehlende Daten:", "NA")

if input_file and delimiter:
    original_df, cleaned_df, space_removal_counts = process_file(input_file, delimiter, default_value)
    
    if original_df is not None and cleaned_df is not None:
        st.write("### Originaldaten Vorschau")
        st.dataframe(original_df.head())

        st.write("### Bereinigte Daten Vorschau")
        st.dataframe(cleaned_df.head())

        st.write("### Bereinigungszusammenfassung")
        st.write(f"Ursprüngliche Zeilen: {len(original_df)}, Bereinigte Zeilen: {len(cleaned_df)}")

        # Analyse der Zeichenersetzungen
        replaced_chars, char_replacement_counts = character_replacement_analysis(original_df, cleaned_df)
        
        st.write("### Analyse der Zeichenersetzung")
        st.write(f"Anzahl der ersetzen Zeichen: {char_replacement_counts}")
        
        if char_replacement_counts > 0:
            st.write("Ersetzte Zeichen:")
            st.dataframe(replaced_chars.head())

        # Analyse der Leerzeichenentfernung
        st.write("### Analyse der Leerzeichenentfernung")
        st.write(f"Anzahl der entfernten Leerzeichen: {space_removal_counts}")

        # Download-Link für bereinigte Daten
        cleaned_csv = cleaned_df.to_csv(index=False, sep=";")
        st.download_button(label="Bereinigte Daten herunterladen", data=cleaned_csv, file_name="bereinigte_daten.csv", mime="text/csv")

else:
    st.error("Bitte laden Sie eine CSV- oder TXT-Datei hoch und geben Sie das Trennzeichen an.")
