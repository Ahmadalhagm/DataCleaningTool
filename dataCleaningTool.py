import streamlit as st
import pandas as pd
import chardet
import io
import re
import csv
import os

def detect_encoding(file_content):
    result = chardet.detect(file_content)
    encoding = result['encoding']
    return encoding, file_content

def remove_foreign_characters(value):
    pattern = re.compile(r'[^\w\s.,;@#\-_äöüÄÖÜß&]+')
    removed_chars = pattern.findall(value)
    new_value = pattern.sub('', value)
    return new_value, ''.join(set(removed_chars))

def process_file(input_file, delimiter, remove_empty_or_space_columns):
    content = input_file.getvalue()
    encoding, content = detect_encoding(content)
    try:
        decoded_content = content.decode(encoding)
        original_df = pd.read_csv(io.StringIO(decoded_content), sep=delimiter, header=None, encoding='utf-8-sig')

        original_df.replace('', pd.NA, inplace=True)
        original_df.dropna(axis=1, how='all', inplace=True)
        original_df.replace(pd.NA, '', inplace=True)

        original_df = original_df.astype(str)
        df = original_df.copy()

        placeholder_count = df.isin(['nan']).sum().sum()
        nan_at_end_count = (df.apply(lambda row: row.iloc[-1] == 'nan', axis=1)).sum()

        space_removal_counts = {}
        foreign_characters_removed = {}
        total_foreign_characters_removed = set()

        remove_spaces_columns = st.multiselect("Wählen Sie die Spalten aus, aus denen Sie alle Leerzeichen entfernen möchten:", ['Alle Spalten'] + original_df.columns.tolist(), default=None)

        for col in df.columns:
            original_col = df[col].copy()
            if col in remove_spaces_columns or 'Alle Spalten' in remove_spaces_columns:
                df[col] = df[col].str.replace('\s+', '', regex=True)
                space_removal_counts[col] = (original_col.str.len() - df[col].str.len()).sum()

            df[col], removed_chars = zip(*df[col].apply(remove_foreign_characters))
            foreign_characters_removed[col] = ''.join(set().union(*removed_chars))
            total_foreign_characters_removed.update(foreign_characters_removed[col])

        df.fillna('', inplace=True)
        df.replace('nan', None, inplace=True)

        return original_df, df, placeholder_count, nan_at_end_count, space_removal_counts, foreign_characters_removed, total_foreign_characters_removed, encoding
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")
        return None, None, None, None, None, None, None, None

def merge_columns(df, merge_columns):
    for i in range(1, len(merge_columns)):
        mask = df.apply(lambda row: row.iloc[-1] != 'nan', axis=1)
        df.loc[mask, merge_columns[0]] = df.loc[mask, merge_columns[0]] + ', ' + df.loc[mask, merge_columns[i]]
        df.loc[mask, merge_columns[i]] = ''  # Clear the values in the selected columns
    return df

def remove_spaces(selected_columns, df):
    if 'Alle Spalten' in selected_columns:
        df = df.apply(lambda col: col.str.replace('\s+', '', regex=True))
    else:
        for col in selected_columns:
            df[col] = df[col].str.replace('\s+', '', regex=True)
    return df

def shift_values_left(selected_column, df):
    if selected_column in df.columns:
        selected_column_index = df.columns.get_loc(selected_column)
        if selected_column_index > 0:
            rows_with_values_at_end = df.apply(lambda row: row.iloc[-1] not in [None, 'nan', ''], axis=1)
            df.loc[rows_with_values_at_end, selected_column] = df.loc[rows_with_values_at_end, selected_column] + ', ' + df.loc[rows_with_values_at_end, selected_column_index + 1]
            for i in range(selected_column_index + 1, len(df.columns) - 1):
                df.loc[rows_with_values_at_end, df.columns[i]] = df.loc[rows_with_values_at_end, df.columns[i+1]]
            df.iloc[:, -1] = None  
    return df

def statistical_analysis(original_df, cleaned_df, placeholder_count, nan_at_end_count, space_removal_counts, foreign_characters_removed, total_foreign_characters_removed, encoding):
    stats_info = {
        "Encoding": encoding,
        "Original DataFrame Size": original_df.shape,
        "Cleaned DataFrame Size": cleaned_df.shape,
        "Placeholder Value Count": placeholder_count,
        "NaN at End Count": nan_at_end_count,
        "Space Removal Counts": space_removal_counts,
        "Foreign Characters Removed": total_foreign_characters_removed,
    }
    return stats_info

st.title("CSV- und TXT-Datei bereinigen und analysieren")

# Options Section
st.sidebar.title("Optionen")
input_file = st.file_uploader("Laden Sie Ihre CSV- oder TXT-Datei hoch:", type=["csv", "txt"])
delimiter = st.sidebar.text_input("Geben Sie das Trennzeichen Ihrer Datei ein:", ";")
remove_empty_or_space_columns = st.sidebar.checkbox("Spalten entfernen, wenn alle Werte Leerzeichen oder None sind")
change_output_encoding = st.sidebar.checkbox("Ändern Sie die Kodierung der Ausgabedatei")

new_encoding = 'utf-8-sig'  # Default encoding for output file

# Analysis Section
if input_file and delimiter:
    original_df, cleaned_df, placeholder_count, nan_at_end_count, space_removal_counts, foreign_characters_removed, total_foreign_characters_removed, encoding = process_file(input_file, delimiter, remove_empty_or_space_columns)
    if original_df is not None and cleaned_df is not None:
        st.write("### Vorschau der Originaldaten")
        st.dataframe(original_df)
        st.write("### Vorschau der bereinigten Daten")
        st.dataframe(cleaned_df)
        
        # Merge Columns Section
        merge_columns_selection = st.multiselect("Wählen Sie zwei oder mehr Spalten zum Zusammenführen aus:", original_df.columns.tolist())
        if len(merge_columns_selection) >= 2:
            if st.button("Spalten zusammenführen"):
                cleaned_df = merge_columns(cleaned_df, merge_columns_selection)
                st.write("### Bereinigte Daten nach Zusammenführen der Spalten")
                st.dataframe(cleaned_df)
        else:
            st.warning("Bitte wählen Sie mindestens zwei Spalten zum Zusammenführen aus.")
        
        # Shift Values Section
        shift_column = st.selectbox("Wählen Sie eine Spalte aus, bis zu der alle Werte verschoben werden sollen:", original_df.columns.tolist())
        if shift_column:
            if st.button("Werte nach links verschieben"):
                cleaned_df = shift_values_left(shift_column, cleaned_df)
                st.write("### Bereinigte Daten nach dem Verschieben der Werte nach links")
                st.dataframe(cleaned_df)
        
        # Analysis Expandable Section
        with st.expander("Analyse", expanded=False):
            st.write("#### Datenbereinigungsanalyse")
            st.write(f"Dateikodierung: {encoding}")
            st.write(f"Ursprüngliche Zeilen: {len(original_df)}, Ursprüngliche Spalten: {original_df.shape[1]}")
            st.write(f"Bereinigte Zeilen: {len(cleaned_df)}, Bereinigte Spalten: {cleaned_df.shape[1]}")
            st.write(f"Anzahl der Platzhalterwerte 'nan' in den ursprünglichen Daten: {placeholder_count}")
            st.write(f"Anzahl der 'nan' am Ende einer Zeile in den ursprünglichen Daten: {nan_at_end_count}")
            st.write(f"Entfernte fremde Zeichen: {', '.join(total_foreign_characters_removed)}")
            for col, count in space_removal_counts.items():
                st.write(f"Anzahl der entfernten Leerzeichen in Spalte '{col}': {count}")
            
            # Statistical Summary for numerical data
            if not cleaned_df.select_dtypes(include='object').empty:
                st.write("### Erweiterte statistische Analyse für numerische Daten")
                stats_info = statistical_analysis(original_df, cleaned_df, placeholder_count, nan_at_end_count, space_removal_counts, foreign_characters_removed, total_foreign_characters_removed, encoding)
                st.write("#### Weitere Informationen")
                st.write(stats_info)
        
        # Download Button for Cleaned Data
        cleaned_csv_buffer = io.StringIO()
        cleaned_df.to_csv(cleaned_csv_buffer, index=False, header=False, sep=delimiter, quoting=csv.QUOTE_NONNUMERIC, encoding=new_encoding)  # Specify UTF-8 with BOM encoding
        cleaned_csv_data = cleaned_csv_buffer.getvalue()
        cleaned_csv_buffer.seek(0)
        st.download_button(label="Bereinigte Daten herunterladen", data=cleaned_csv_data.encode(new_encoding), file_name=os.path.splitext(input_file.name)[0] + "_bereinigt.csv", mime="text/csv")
