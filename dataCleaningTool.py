import streamlit as st
import pandas as pd
import chardet
import io

def detect_encoding(file_content):
    result = chardet.detect(file_content)
    encoding = result['encoding']
    return encoding

def process_file(input_file, delimiter, default_value="NA"):
    content = input_file.getvalue()
    encoding = detect_encoding(content)

    try:
        # Laden der Originaldaten
        original_df = pd.read_csv(io.StringIO(content.decode(encoding)),
                                  sep=delimiter,
                                  encoding=encoding)

        # Erstellen einer Kopie des DataFrames für die Bereinigung, um die Originaldaten zu erhalten
        df = original_df.copy()

        # Bereinigungsoperationen
        space_removal_counts = 0
        for col in df.select_dtypes(include=['object']).columns:
            # Entfernen von Zeichen, die keine Buchstaben, Zahlen, Punkte, Kommas oder Leerzeichen sind
            df[col] = df[col].str.replace('[^a-zA-Z0-9., ]', '', regex=True)

            # Entfernen von Leerzeichen am Ende jedes Werts, ohne Leerzeichen innerhalb von Wörtern zu beeinflussen
            df[col] = df[col].str.rstrip()

            # Entfernen von Pipe-Zeichen am Ende jedes Werts
            df[col] = df[col].str.rstrip('|')

            # Zählen der entfernten Leerzeichen am Ende jedes Werts
            space_removal_counts += (original_df[col].str.len() - original_df[col].str.rstrip().str.len()).sum()

        df.fillna(default_value, inplace=True)

        return original_df, df, space_removal_counts  # Rückgabe sowohl des Original- als auch des bereinigten DataFrames
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")
        return None, None, None

def character_replacement_analysis(original_df, cleaned_df):
    # Analyse der Zeichenersetzungen
    replaced_chars = original_df.select_dtypes(include=['object']).replace(cleaned_df)
    char_replacement_counts = (original_df != cleaned_df).sum().sum()

    return replaced_chars, char_replacement_counts

# Streamlit UI-Setup
st.title("CSV-Datei bereinigen und analysieren")

input_file = st.file_uploader("Laden Sie Ihre CSV-Datei hoch:", type="csv")
delimiter = st.text_input("Geben Sie das Trennzeichen Ihrer CSV-Datei ein:", ",")
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
        cleaned_csv = cleaned_df.to_csv(index=False)
        st.download_button(label="Bereinigte Daten herunterladen", data=cleaned_csv, file_name="bereinigte_daten.csv", mime="text/csv")

else:
    st.error("Bitte laden Sie eine CSV-Datei hoch und geben Sie das Trennzeichen an.")
