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
        original_df = pd.read_csv(io.StringIO(content.decode(encoding)),
                                  sep=delimiter,
                                  encoding=encoding,
                                  on_bad_lines='skip')

        # Create a copy of the DataFrame for cleaning to preserve the original data
        df = original_df.copy()

        # Cleaning operations
        for col in df.select_dtypes(include=['object']).columns:
            # Remove characters that are not letters, numbers, periods, commas, or spaces
            df[col] = df[col].str.replace('[^a-zA-Z0-9., ]', '', regex=True)

            # Remove trailing spaces without affecting spaces within words
            df[col] = df[col].str.rstrip()

            # Remove trailing pipe characters
            df[col] = df[col].str.rstrip('|')

        df.fillna(default_value, inplace=True)

        return original_df, df  # Return both the original and cleaned DataFrame
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None, None

def character_replacement_analysis(original_df, cleaned_df):
    # Analysis of character replacements
    replaced_chars = original_df.select_dtypes(include=['object']).replace(cleaned_df)
    char_replacement_counts = (original_df != cleaned_df).sum().sum()

    return replaced_chars, char_replacement_counts

def space_removal_analysis(original_df, cleaned_df):
    # Analysis of space removal
    space_removal_counts = ((original_df != cleaned_df) & (original_df == " ")).sum().sum()
    
    return space_removal_counts

# Streamlit UI setup
st.title("Deutsche Glasfaser Data Cleaning Tool")

input_file = st.file_uploader("Upload your CSV file:", type="csv")
delimiter = st.text_input("Enter the delimiter used in your CSV file:", ";")
default_value = st.text_input("Default value for missing data:", "NA")

if st.button("Clean and Analyze"):
    if input_file and delimiter:
        original_df, cleaned_df = process_file(input_file, delimiter, default_value)
        
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
            space_removal_counts = space_removal_analysis(original_df, cleaned_df)
            
            st.write("### Space Removal Analysis")
            st.write(f"Number of Spaces Removed: {space_removal_counts}")

            # Save the cleaned data to a CSV file
            cleaned_filename = "cleaned_data.csv"
            cleaned_df.to_csv(cleaned_filename, index=False)
            
            # Provide a download link for the cleaned data
            st.write("### Download Cleaned Data")
            st.markdown(f"Download the cleaned data as [cleaned_data.csv](sandbox:/mnt/data/{cleaned_filename})")
    else:
        st.error("Please upload a CSV file and specify the delimiter.")
