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
        # Load the original data
        if input_file.name.endswith('.csv'):
            original_df = pd.read_csv(io.StringIO(content.decode(encoding)),
                                      sep=delimiter,
                                      encoding=encoding)
        elif input_file.name.endswith('.txt'):
            original_df = pd.read_csv(io.StringIO(content.decode(encoding)),
                                      sep=delimiter,
                                      encoding=encoding,
                                      header=None)
        else:
            st.error("Nur .csv- und .txt-Dateien werden unterstützt.")
            return None, None, None

        # Check for unnamed columns at the end
        unnamed_columns = [col for col in original_df.columns if 'Unnamed:' in col]
        if unnamed_columns:
            # Check if there are enough columns to check for email values before and after the unnamed columns
            for col in unnamed_columns:
                idx = original_df.columns.get_loc(col)
                if idx >= 1 and idx < len(original_df.columns) - 1:
                    before_col = original_df.columns[idx - 1]
                    after_col = original_df.columns[idx + 1]
                    
                    # Check if there are at least three columns before and after the unnamed column
                    if idx >= 2 and idx < len(original_df.columns) - 2:
                        if original_df[before_col].str.contains('@').all() and original_df[after_col].str.contains('@').all():
                            # Merge email addresses from before and after columns
                            original_df[before_col] = original_df[before_col].astype(str) + ', ' + original_df[after_col].astype(str)
                            original_df.drop(columns=[col, after_col], inplace=True)
                        else:
                            st.warning("Es wurden keine E-Mail-Adressen in den Spalten gefunden.")
                    else:
                        st.warning("Nicht genügend Spalten vorhanden, um E-Mail-Adressen zu überprüfen.")

        # Create a copy of the DataFrame for cleaning to preserve the original data
        df = original_df.copy()

        # Cleaning operations
        space_removal_counts = 0
        for col in df.select_dtypes(include=['object']).columns:
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
        cleaned_csv = cleaned_df.to_csv(index=False)
        st.download_button(label="Bereinigte Daten herunterladen", data=cleaned_csv, file_name="bereinigte_daten.csv", mime="text/csv")

else:
    st.error("Bitte laden Sie eine CSV- oder TXT-Datei hoch und geben Sie das Trennzeichen an.")
