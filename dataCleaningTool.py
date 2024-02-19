import streamlit as st
import pandas as pd
import chardet
import io

def detect_encoding(file_content):
    result = chardet.detect(file_content)
    encoding = result['encoding']
    return encoding, file_content

def remove_foreign_characters(value):
    if pd.isna(value):
        return "", ""
    pattern = re.compile(r'[^\w\s.,;@#\-_äöüÄÖÜß&]+')
    removed_chars = pattern.findall(str(value))
    new_value = pattern.sub('', str(value))
    return new_value, ''.join(set(removed_chars))

def process_file(input_file, delimiter, remove_spaces_columns, merge_columns_selection, merge_separator, remove_empty_or_space_columns):
    content = input_file.getvalue()
    encoding_before, content = detect_encoding(content)
    try:
        decoded_content = content.decode(encoding_before)
        original_df = pd.read_csv(io.StringIO(decoded_content), sep=delimiter, dtype=str)
        df = original_df.copy()

        cleaning_summary = {
            'empty_columns_removed': 0,
            'encoding_before': encoding_before,
            'file_size_before_kb': len(content) / 1024,
        }

        # Removing spaces from specified columns or all columns
        if 'All' in remove_spaces_columns:
            df = df.applymap(lambda x: x.replace(' ', '') if type(x) == str else x)
        else:
            for col in remove_spaces_columns:
                df[col] = df[col].apply(lambda x: x.replace(' ', '') if type(x) == str else x)

        # Merging specified columns
        if len(merge_columns_selection) == 2:
            col1, col2 = [df.columns[int(c)-1] for c in merge_columns_selection]
            df[col1] = df[col1].astype(str) + merge_separator + df[col2].astype(str)
            df.drop(col2, axis=1, inplace=True)

        # Remove empty columns if selected
        if remove_empty_or_space_columns:
            initial_columns = df.shape[1]
            df.dropna(axis=1, how='all', inplace=True)
            cleaning_summary['empty_columns_removed'] = initial_columns - df.shape[1]

        # Cleaning summary update
        cleaning_summary.update({
            'file_size_after_kb': df.memory_usage(deep=True).sum() / 1024,
            'rows_before': original_df.shape[0],
            'rows_after': df.shape[0],
            'columns_before': original_df.shape[1],
            'columns_after': df.shape[1],
        })

        return original_df, df, cleaning_summary
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None, None, None

st.title("CSV- und TXT-Datei bereinigen und analysieren")

input_file = st.file_uploader("Laden Sie Ihre CSV- oder TXT-Datei hoch:", type=["csv", "txt"])
delimiter = st.text_input("Geben Sie das Trennzeichen Ihrer Datei ein:", ";")

if input_file is not None:
    column_options = [str(i) for i in range(1, pd.read_csv(input_file, nrows=0, delimiter=delimiter).shape[1] + 1)]
    remove_empty_or_space_columns = st.checkbox("Spalten entfernen, wenn alle Werte Leerzeichen oder None sind")
    remove_spaces_columns = st.multiselect("Wählen Sie die Spalten aus, aus denen Sie alle Leerzeichen entfernen möchten:", ['All'] + column_options, default=[])
    merge_columns_selection = st.multiselect("Wählen Sie zwei Spalten zum Zusammenführen aus:", column_options, default=[])
    merge_separator = st.text_input("Geben Sie den Trennzeichen für das Zusammenführen der Spalten ein:", ",")

    if st.button('Process File'):
        original_df, cleaned_df, cleaning_summary = process_file(input_file, delimiter, remove_spaces_columns, merge_columns_selection, merge_separator, remove_empty_or_space_columns)
        
        if original_df is not None and cleaned_df is not None:
            st.write("### Original Data Overview")
            st.write(f"Rows: {original_df.shape[0]}, Columns: {original_df.shape[1]}")
            st.dataframe(original_df.head())
            
            st.write("### Cleaned Data Overview")
            st.write(f"Rows: {cleaned_df.shape[0]}, Columns: {cleaned_df.shape[1]}")
            st.dataframe(cleaned_df.head())
            
            st.write("### Cleaning Summary")
            for key, value in cleaning_summary.items():
                st.write(f"{key.replace('_', ' ').capitalize()}: {value}")

            # Download button for the cleaned data
            cleaned_csv = cleaned_df.to_csv(index=False, sep=delimiter).encode('utf-8')
            st.download_button(label="Download Cleaned Data",
                               data=cleaned_csv,
                               file_name=f"cleaned_{os.path.basename(input_file.name)}",
                               mime="text/csv")
