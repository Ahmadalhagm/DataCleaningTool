import streamlit as st
import pandas as pd
import chardet
import io
import os
import csv

def detect_encoding(file_content):
    result = chardet.detect(file_content)
    encoding = result['encoding']
    return encoding, file_content

def process_file(input_file, delimiter, remove_spaces_columns, merge_columns, merge_separator, remove_empty_or_space_columns, detect_column_names):
    content = input_file.getvalue()
    encoding, content = detect_encoding(content)
    try:
        decoded_content = content.decode(encoding)
        original_df = pd.read_csv(io.StringIO(decoded_content), sep=delimiter, header=None)

        if detect_column_names:
            original_df.columns = original_df.iloc[0]
            original_df = original_df.drop(original_df.index[0])

        if remove_empty_or_space_columns:
            original_df.replace('', pd.NA, inplace=True)
            original_df.dropna(axis=1, how='all', inplace=True)
            original_df.replace(pd.NA, '', inplace=True)

        original_df = original_df.astype(str)
        df = original_df.copy()

        if merge_columns:
            merged_column_name = df.columns[min(merge_columns)]
            df[merged_column_name] = df[merge_columns].astype(str).apply(lambda x: merge_separator.join(x), axis=1)
            df.drop(columns=[df.columns[i] for i in merge_columns if i != min(merge_columns)], inplace=True)

        space_removal_counts = {}
        total_foreign_characters_removed = set()

        for col in df.columns:
            original_col = df[col].copy()
            if col in remove_spaces_columns or 'All Columns' in remove_spaces_columns:
                df[col] = df[col].str.replace('\s+', '', regex=True)
                space_removal_counts[col] = (original_col.str.len() - df[col].str.len()).sum()

        df.fillna('', inplace=True)
        df.replace('nan', None, inplace=True)

        return original_df, df, space_removal_counts, encoding
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")
        return None, None, None, None

def find_rows_without_semicolon_at_end(df):
    rows_without_semicolon_at_end = []
    if not df.empty:
        for idx, row in df.iterrows():
            if not row.iloc[-1].endswith(';'):
                rows_without_semicolon_at_end.append(idx)
    return rows_without_semicolon_at_end

st.title("CSV- und TXT-Datei bereinigen und analysieren")
input_file = st.file_uploader("Laden Sie Ihre CSV- oder TXT-Datei hoch:", type=["csv", "txt"])
delimiter = st.text_input("Geben Sie das Trennzeichen Ihrer Datei ein:", ";")
remove_empty_or_space_columns = st.checkbox("Spalten entfernen, wenn alle Werte Leerzeichen oder None sind")
detect_column_names = st.checkbox("Spaltennamen erkennen")
column_options = "100"
try:
    max_columns = int(column_options)
    column_range = list(range(max_columns))
except ValueError:
    st.error("Bitte geben Sie eine gültige Zahl ein.")
remove_spaces_columns = st.multiselect("Wählen Sie die Spalten aus, aus denen Sie alle Leerzeichen entfernen möchten:", ['All Columns'] + column_range, default=[])
merge_columns_selection = st.multiselect("Wählen Sie zwei oder mehr Spalten zum Zusammenführen aus:", column_range, default=[])
merge_separator = st.text_input("Geben Sie den Trennzeichen für das Zusammenführen der Spalten ein:", ",")

if input_file and delimiter:
    original_df, cleaned_df, space_removal_counts, encoding = process_file(input_file, delimiter, remove_spaces_columns, merge_columns_selection, merge_separator, remove_empty_or_space_columns, detect_column_names)
    if original_df is not None and cleaned_df is not None:
        st.write("### Vorschau der Originaldaten")
        st.dataframe(original_df.head())
        st.write("### Vorschau der bereinigten Daten")
        st.dataframe(cleaned_df.head())
        
        rows_without_semicolon_at_end = find_rows_without_semicolon_at_end(cleaned_df)
        if rows_without_semicolon_at_end:
            st.write("### Zeilen ohne Semikolon am Ende")
            for row_idx in rows_without_semicolon_at_end:
                st.write(f"Zeile {row_idx + 1}: {'; '.join(cleaned_df.iloc[row_idx])}")
                col_to_replace_separator = st.selectbox("Wählen Sie die Spalte, in der der Separator ersetzt werden soll:", cleaned_df.columns)
                cleaned_df[col_to_replace_separator] = cleaned_df[col_to_replace_separator].str.replace(';', ',')
            st.write("### Bereinigte Daten")
            st.dataframe(cleaned_df)

        with st.expander("Analyse", expanded=False):
            st.write("#### Datenbereinigungsanalyse")
            st.write(f"Dateikodierung: {encoding}")
            st.write(f"Ursprüngliche Zeilen: {len(original_df)}, Ursprüngliche Spalten: {original_df.shape[1]}")
            st.write(f"Bereinigte Zeilen: {len(cleaned_df)}, Bereinigte Spalten: {cleaned_df.shape[1]}")
            for col, count in space_removal_counts.items():
                st.write(f"Leerzeichen entfernt in Spalte '{col}': {count}")
            
        cleaned_csv_buffer = io.StringIO()
        cleaned_df.to_csv(cleaned_csv_buffer, index=False, header=True, sep=delimiter, quoting=csv.QUOTE_NONNUMERIC, encoding='utf-8-sig')
        cleaned_csv_data = cleaned_csv_buffer.getvalue()
        cleaned_csv_buffer.seek(0)
        st.download_button("Bereinigte Daten herunterladen", data=cleaned_csv_data.encode('utf-8-sig'), file_name=os.path.splitext(input_file.name)[0] + "_bereinigt.csv", mime="text/csv")
