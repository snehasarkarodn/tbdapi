import os
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
import numpy as np
from django.http import FileResponse,HttpResponse
from openpyxl.styles import PatternFill
import openpyxl
import json
import requests
import re
import xlwings as xw


#Importing from preprocessing_functions_sub.py
from preprocessing.preprocessing_functions_sub import key_value_pair_modified
#importing from GPT_atribute_generation_sub_func
from preprocessing.GPT_atribute_generation_sub_func import attribute_generation_prompt
from preprocessing.GPT_atribute_generation_sub_func import chat_with_model
# from preprocessing.GPT_atribute_generation_sub_func import convert_to_dictionary_from_string
# from preprocessing.GPT_atribute_generation_sub_func import user_prompt_for_attribute_generation
from preprocessing.GPT_atribute_generation_sub_func import url_to_base64
from preprocessing.GPT_atribute_generation_sub_func import attribute_prompt_parser
from preprocessing.GPT_atribute_generation_sub_func import create_model_class_def

from Table_update_Mysql.sub_func import fetch_from_db

#importing db connections
# from utils.mysql_db_utils import get_db_cursor

def del_file_or_folder(path):   
    if os.path.isdir(path):
        # If it's a directory, delete all its contents
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                os.remove(file_path)
            for name in dirs:
                dir_path = os.path.join(root, name)
                os.rmdir(dir_path)
        # Finally, delete the directory itself
        os.rmdir(path)
    elif os.path.isfile(path):
        # If it's a file, delete it directly
        os.remove(path)
    else:
        print(f"The path {path} does not exist.")


def Convert_InputSheet_Data_to_Dict(incoming_sheet_with_mandate_columns,incoming_sheet_without_mandate_columns,unique_identifier,copied_temp_file_path,inputsheet_filename,inputsheet_extension):
    #Making the headers and its 1st row, a pair , where incoming_sheet is a pandas dataframe.
    mandatory_key_value_pair=dict(incoming_sheet_with_mandate_columns.iloc[0])

    #transforming the data to a organised dictionary.
    mandatory_key_value_pair_modified = {}
    for key, value in mandatory_key_value_pair.items():
        if key.startswith('Unnamed:'):
            new_key = 'Unnamed'
        else:
            new_key = key.split('.')[0]
        
        if new_key in mandatory_key_value_pair_modified:
            if isinstance(mandatory_key_value_pair_modified[new_key], list):
                mandatory_key_value_pair_modified[new_key].append(value)
            else:
                mandatory_key_value_pair_modified[new_key] = [mandatory_key_value_pair_modified[new_key], value]
        else:
            mandatory_key_value_pair_modified[new_key] = value
    
    Seller_Mandatory_columns = mandatory_key_value_pair_modified['Seller_Mandatory']
    # print("Seller_Mandatory_columns",Seller_Mandatory_columns)
    Seller_Mandatory_df = incoming_sheet_without_mandate_columns[Seller_Mandatory_columns]

    missing_values_dict = {}
    for index, row in Seller_Mandatory_df.iterrows():
        if str(row[unique_identifier]).endswith('$P'):
            pass
        else:
            missing_columns = row[row.isna()].index.tolist()
            # print(missing_columns)
            
            if missing_columns:
                missing_indices = {}
                for col in missing_columns:
                    missing_indices[col] = (index+2, Seller_Mandatory_df.columns.get_loc(col) + 1)
                missing_values_dict[row[unique_identifier]] = missing_indices
    # print("missing_values_dict",missing_values_dict)
    found_missing_cells = []
    for key in missing_values_dict.keys():
        found_missing_cells.append(list(missing_values_dict[key].values()))

    found_cells = [item for sublist in found_missing_cells for item in sublist]
    
    return(Seller_Mandatory_df,found_cells)

def remove_ending_with_P(input_list):
    return [item for item in input_list if not str(item).endswith('$P')]

def SKU_Identy_verification_QC1(image_unique_identifier_list, sheet_unique_identifier_list= None, copied_temp_file_path= None, inputsheet_filename= None, inputsheet_extension= None):
    sheet_unique_identifier_list_updated = remove_ending_with_P(sheet_unique_identifier_list)
    # print("sheet_unique_identifier_list",sheet_unique_identifier_list)
    # print("sheet_unique_identifier_list_updated",sheet_unique_identifier_list_updated)
    missing_identifier_in_image = [element for element in sheet_unique_identifier_list_updated if element not in image_unique_identifier_list]
    missing_identifier_in_sheet = [element for element in image_unique_identifier_list if element not in sheet_unique_identifier_list_updated]
    # print("missing_identifier_in_image", missing_identifier_in_image)
    # print("missing_identifier_in_sheet", missing_identifier_in_sheet)
    result = {
        "status": "pass",
        "data": None,
        "message": ""
    }

    try:
        
        if missing_identifier_in_image:
            data= {}
            if missing_identifier_in_image not in missing_identifier_in_sheet:
                
                data["missing_skus_in_image"] = missing_identifier_in_image
            
            QC1_df = pd.DataFrame(data)
            with pd.ExcelWriter(copied_temp_file_path, engine='openpyxl', mode='a') as writer:
                QC1_df.to_excel(writer, sheet_name='QC1', index=False)

            result["status"] = "fail"
            result["data"] = copied_temp_file_path
            result["message"] = "QC1 check failed. See QC1 sheet in the Excel file for details."
            print("QC1 entered and finished with data")
        else:
            print("QC1 Not entered")
    
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)
        print(f"Error in SKU_Identy_verification_QC1: {e}")

    return result
    
def image_path_structure_convert(image_files):
    image_path_dict = {}
    # Iterate through the file paths
    for path in image_files:    
        unique_subfolder = path.split('/')[0]
        image_name = path.split('/')[1]
        if unique_subfolder in image_path_dict:
            image_path_dict[unique_subfolder].append(image_name)
        else:
            image_path_dict[unique_subfolder] = [image_name]
    return(image_path_dict)


def Get_all_Headers(incoming_sheet_with_mandate_columns):
    
    key_value_pair_modifiedd = key_value_pair_modified(incoming_sheet_with_mandate_columns)
    
    ####df_dict####
    ODN_Mandatory_Headers = key_value_pair_modifiedd['ODN_Mandatory']
    Seller_Mandatory_Headers = key_value_pair_modifiedd['Seller_Mandatory']
    Optional_Headers = key_value_pair_modifiedd['Optional']

    Seller_ODN_Optional_IMT_Mandatory_Headers = key_value_pair_modifiedd['Seller_ODN_Optional_IMT_Mandatory']
    ODN_Optional_IMT_Mandatory_Headers = key_value_pair_modifiedd['ODN_Optional_IMT_Mandatory']
    Remove_Headers = ['Product Title', 'Description','Generic Keywords','Bullet Point 1(AM)',
    'Bullet Point 2(AM)','Bullet Point 3(AM)','Bullet Point 4(AM)','Bullet Point 5(AM)',]

    gpt_mandate_Headers=list(set(Seller_ODN_Optional_IMT_Mandatory_Headers + ODN_Optional_IMT_Mandatory_Headers)-set(Remove_Headers))

    return (ODN_Mandatory_Headers,Seller_Mandatory_Headers,gpt_mandate_Headers,Optional_Headers)


def df_dict_find(incoming_sheet_with_mandate_columns,df_Dropdown_Values_df):

    #transforming the data to a organised dictionary.
    key_value_pair_modifiedd = key_value_pair_modified(incoming_sheet_with_mandate_columns)
    
    ####df_dict####
    ODN_Mandatory_Headers=key_value_pair_modifiedd['ODN_Mandatory']
    Seller_Mandatory_Headers=key_value_pair_modifiedd['Seller_Mandatory']
    Seller_ODN_Optional_IMT_Mandatory_Headers = key_value_pair_modifiedd['Seller_ODN_Optional_IMT_Mandatory']
    ODN_Optional_IMT_Mandatory_Headers = key_value_pair_modifiedd['ODN_Optional_IMT_Mandatory']
    Remove_Headers = ['Product Title', 'Description','Generic Keywords','Bullet Point 1(AM)',
    'Bullet Point 2(AM)','Bullet Point 3(AM)','Bullet Point 4(AM)','Bullet Point 5(AM)',]

    GPT_Fetched_Headers_For_Attr_Gen=list(set(Seller_ODN_Optional_IMT_Mandatory_Headers + ODN_Optional_IMT_Mandatory_Headers)-set(Remove_Headers))

    df_Dropdown_Values_df=df_Dropdown_Values_df[GPT_Fetched_Headers_For_Attr_Gen]
    df_dict = {col: df_Dropdown_Values_df[col].unique().tolist() for col in df_Dropdown_Values_df.columns}

    return (df_dict)

def create_final_df_dict(cat, sub, incoming_sheet_with_mandate_columns, df_Dropdown_Values_df):
    db_data = fetch_from_db(cat, sub)
    df_dict = df_dict_find(incoming_sheet_with_mandate_columns, df_Dropdown_Values_df)
    db_data_dict = {item['attributes']: item for item in db_data}
    final_df_dict = {}
    unique_prompt = None
    unique_image_angles = set()

    for key, values in df_dict.items():
        if key in db_data_dict:
            description = db_data_dict[key]['description']
            prompt = db_data_dict[key]['prompt']
            image_angles = db_data_dict[key]['image_angle'].split(',')
            unique_prompt = prompt if unique_prompt is None else unique_prompt
            unique_image_angles.update(image_angles)
        else:
            description = ""
            image_angles = []

        final_df_dict[key] = {
            'description': description,
            'values': values
        }

    return final_df_dict, unique_prompt, list(unique_image_angles)

def sku_unique_id_image_url_dictionary_func(odnconnectLink,image_path_dict):
    http = "https://"
    addition="/"    
    image_extensions = ['.jpg', '.jpeg', '.png', '.JPG']
    sku_unique_id_image_url_dictionary = {}
    for key, value in image_path_dict.items(): 
        matching_filenames = [filename for filename in value if (filename.endswith(f'_1{ext}') or filename.endswith(f'_4{ext}') for ext in image_extensions)]   
        # print('links', matching_filenames)
        if matching_filenames:
            value = f"{http}{odnconnectLink}{key}{addition}{matching_filenames[0]}"
            sku_unique_id_image_url_dictionary[key]=value       

    return (sku_unique_id_image_url_dictionary)

def sku_all_image_url_dictionary_func(odnconnectLink,image_path_dict):
    http = "https://"
    addition="/"    
    image_extensions = ['.jpg', '.jpeg', '.png']
    sku_all_image_url_dictionary = {}
    for key, value in image_path_dict.items():
        image_list = []
        for image in value:
            value = f"{http}{odnconnectLink}{key}{addition}{image}"
            image_list.append(value)
        
        sku_all_image_url_dictionary[key]=image_list        
        
    return (sku_all_image_url_dictionary)



def convert_image_links(input_dict):
    output_dict = {}
    # print(input_dict)
    import time
    for key, links in input_dict.items():
        output_dict[key] = {}
        for i , link in enumerate(links):
            # print(link)
            # Extract the filename from the URL
            filename = link.split('/')[-1]
            # print(filename)
            # Use regex to find the number at the end of the filename
            match = re.search(r'[-_](\d+)\.(?:jpg|jpeg|png|gif|bmp|jpeg)$', filename, re.IGNORECASE)
            if match:
                number = int(match.group(1))
                if 1 <= number <= 50:  # This covers numbers 1 to 20
                    output_dict[key][f"Images_{number}"] = link
            
            else:
                output_dict[key][f"Images_{i+1}"] = link


    
    return output_dict
    

def image_attribute_fetch_dictionary_func(cat: str, sub_category: str, upload_files_dict: dict, df_dict: dict, prompt: str, image_angle: list):
    #####Data Received#####
    try:
        sku_unique_id_image_url_dictionary = convert_image_links(upload_files_dict)
        # print("sku_unique_id_image_url_dictionary",sku_unique_id_image_url_dictionary)
        df_dict = df_dict
        ##########
        image_attribute_fetch_dictionary = {}
        for sku, images in sku_unique_id_image_url_dictionary.items():
            links = []
            for Images_name, image_links in images.items():
                if Images_name in image_angle:
                    links.append(image_links)
            # print(links)
            
            # print("links",links)
            
            sku = sku
            format_class = create_model_class_def(df_dict, sku, cat, sub_category)
            init_prompt = prompt
            user_prompt, parser = attribute_prompt_parser(init_prompt, format_class)
            # print('final_prompt: ', user_prompt)
            urls = links

            base64_images_list = url_to_base64(urls)

            message = attribute_generation_prompt(user_prompt,base64_images_list)

            # print("message",message)
            attributes, token_amount=chat_with_model(message)
            # print("attributes",attributes)
            final_output = parser.parse(attributes)
            fetched_attributes = dict(final_output)
            fetched_attributes = {key.replace('__', ' '): value for key, value in fetched_attributes.items()}
            # fetched_attributes = {key.replace('Sub Category', 'Sub-Category'): value if isinstance(key, str) else value for key, value in fetched_attributes.items()}
            # fetched_attributes=convert_to_dictionary_from_string(attributes)
            
            image_attribute_fetch_dictionary[sku]=fetched_attributes
    except Exception as e:
        print(e)
    return(image_attribute_fetch_dictionary)


def get_cat_subcat(inputsheet_filename):
    parts = inputsheet_filename.split('_')

    category = parts[0]
    subcategory = parts[1]
    return(category,subcategory)

def get_sub_UniqueIdentifier_imageURL_dict(original_dict, key):
    if key not in original_dict:
        raise KeyError(f"Key '{key}' not found in the dictionary.")

    return {key: original_dict[key]}


def filter_and_map_to_dict(df, filter_column_name, required_columns_data, sku_codes):

    if filter_column_name not in df.columns:
        raise ValueError(f"Column '{filter_column_name}' not found in DataFrame.")

    missing_columns = [col for col in required_columns_data if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"Columns '{', '.join(missing_columns)}' not found in DataFrame.")
  
    filtered_df = df[df[filter_column_name]==sku_codes]
 
    result = {}
    for _, row in filtered_df.iterrows():
        sku_code = row[filter_column_name]
        result[sku_code] = {col: row[col] for col in required_columns_data}

    return result

def download_content(content, folder_path, filename, extension):
    # Ensure the folder exists
    os.makedirs(folder_path, exist_ok=True)
    final_path = filename + extension

    # Create the full file path
    file_path = os.path.join(folder_path, final_path)

    # Write the content to the file
    with open(file_path, 'wb') as file:
        file.write(content.getvalue())

    print(f"File downloaded successfully: {file_path}")


def process_excel_file(temp_file_path, incoming_sheet):
    app = None
    wb = None
    try:
        app = xw.App(visible=False)
        
        if not os.path.exists(temp_file_path):
            raise FileNotFoundError(f"The file {temp_file_path} does not exist.")
        
        wb = app.books.open(temp_file_path, read_only=False)
        app.enable_events = False
        
        if 'Attributes' not in [sheet.name for sheet in wb.sheets]:
            raise ValueError("The 'Attributes' sheet does not exist in the workbook.")
        
        ws = wb.sheets['Attributes']
        
        if incoming_sheet.empty:
            raise ValueError("The incoming_sheet is empty.")
        
        ws.range('A3').options(index=False, header=False).value = incoming_sheet
        
        wb.save()
        print(f"File saved successfully: {temp_file_path}")
        
    except FileNotFoundError as e:
        print(f"File error: {e}")
    except ValueError as e:
        print(f"Value error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if wb:
            try:
                wb.close()
            except Exception as e:
                print(f"Error closing workbook: {e}")
        if app:
            try:
                app.quit()
            except Exception as e:
                print(f"Error quitting Excel application: {e}")


def convert_seconds_to_minutes_seconds(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60

    return f'{minutes}.{remaining_seconds:02d}'

