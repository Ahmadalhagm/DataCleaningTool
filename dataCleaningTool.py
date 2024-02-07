import streamlit as st
import pandas as pd
import chardet
import io
import os

def detect_encoding(file_content):
    result = chardet.detect(file_content)
    encoding = result['encoding']
    return encoding

def process_file(input_file, delimiter, default_value="NA"):
    content = input_file.getvalue()
    encoding = detect_encoding(content)

    try:
        # Load the original data
        original_df = pd.read_csv(io.StringIO(content.decode(encoding)),
                                  sep=delimiter,
                                  encoding=encoding)

        # Create a copy of the DataFrame for cleaning to preserve the original data
        df = original_df.copy()

        # Cleaning operations
        space_removal_counts = 0
        for col in df.select_dtypes(include=['object']).columns:
            # Remove characters that are not letters, numbers, periods, commas, or spaces
            df[col] = df[col].str.replace('[^a-zA-Z0-9., ]', '', regex=True)

            # Remove trailing spaces without affecting spaces within words
            df[col] = df[col].str.rstrip()

            # Remove trailing pipe characters
            df[col] = df[col].str.rstrip('|')

            # Count spaces removed from the end of each value
            space_removal_counts += (original_df[col].str.len() - original_df[col].str.rstrip().str.len()).sum()

        df.fillna(default_value, inplace=True)

        return original_df, df, space_removal_counts  # Return both the original and cleaned DataFrame
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None, None, None

def character_replacement_analysis(original_df, cleaned_df):
    # Analysis of character replacements
    replaced_chars = original_df.select_dtypes(include=['object']).replace(cleaned_df)
    char_replacement_counts = (original_df != cleaned_df).sum().sum()

    return replaced_chars, char_replacement_counts

# Streamlit UI setup
st.title("CSV File Cleaner and Analyzer")

# Export file selector
export_filepath = st.text_input("Enter export file path:", value="output.csv")

input_file = st.file_uploader("Upload your CSV file:", type="csv")
delimiter = st.text_input("Enter the delimiter used in your CSV file:", ",")
default_value = st.text_input("Default value for missing data:", "NA")

if input_file and delimiter:
    original_df, cleaned_df, space_removal_counts = process_file(input_file, delimiter, default_value)
    
    if original_df is not None and cleaned_df is not None:
        st.write("### Original Data Preview")
        st.dataframe(original_df.head())

        st.write("### Cleaned Data Preview")
        st.dataframe(cleaned_df.head())

        st.write("### Cleaning Summary")
        st.write(f"Original Rows: {len(original_df)}, Cleaned Rows: {len(cleaned_df)}")

        # Analysis of character replacements
        replaced_chars, char_replacement_counts = character_replacement_analysis(original_df, cleaned_df)
        
        st.write("### Character Replacement Analysis")
        st.write(f"Number of Characters Replaced: {char_replacement_counts}")
        
        if char_replacement_counts > 0:
            st.write("Replaced Characters:")
            st.dataframe(replaced_chars.head())

        # Analysis of space removal
        st.write("### Space Removal Analysis")
        st.write(f"Number of Spaces Removed: {space_removal_counts}")

        # Export the cleaned data
        if st.button("Export Cleaned Data"):
            try:
                cleaned_df.to_csv(export_filepath, index=False)
                st.success(f"Cleaned data exported to {export_filepath}")
            except Exception as e:
                st.error(f"An error occurred while exporting: {e}")

else:
    st.error("Please upload a CSV file and specify the delimiter.")
