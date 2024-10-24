import os
import re
from open_ai_tbd_gen.gpt_text_gen import create_model_class_def 
from open_ai_tbd_gen.gpt_text_gen import attribute_prompt_parser
from open_ai_tbd_gen.gpt_text_gen import url_to_base64
from open_ai_tbd_gen.gpt_text_gen import attribute_generation_prompt
from open_ai_tbd_gen.gpt_text_gen import chat_with_model

def del_file_or_folder(path):   
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                os.remove(file_path)
            for name in dirs:
                dir_path = os.path.join(root, name)
                os.rmdir(dir_path)
        os.rmdir(path)
    elif os.path.isfile(path):
        os.remove(path)
    else:
        print(f"The path {path} does not exist.")

def convert_image_links(input_dict):
    output_dict = {}
    import time
    for key, links in input_dict.items():
        output_dict[key] = {}
        for i , link in enumerate(links):
            filename = link.split('/')[-1]
            match = re.search(r'[-_](\d+)\.(?:jpg|jpeg|png|gif|bmp|jpeg)$', filename, re.IGNORECASE)
            if match:
                number = int(match.group(1))
                if 1 <= number <= 50:
                    output_dict[key][f"Images_{number}"] = link
            
            else:
                output_dict[key][f"Images_{i+1}"] = link

    return output_dict
    
def image_attribute_fetch_dictionary_func(cat: str, sub_category: str, upload_files_dict: dict, df_dict: dict, prompt: str, image_angle: list):
    try:
        sku_unique_id_image_url_dictionary = convert_image_links(upload_files_dict)
        df_dict = df_dict

        image_attribute_fetch_dictionary = {}
        for sku, images in sku_unique_id_image_url_dictionary.items():
            links = []
            for Images_name, image_links in images.items():
                if Images_name in image_angle:
                    links.append(image_links)

            sku = sku
            format_class = create_model_class_def(df_dict, sku, cat, sub_category)
            init_prompt = prompt
            user_prompt, parser = attribute_prompt_parser(init_prompt, format_class)

            urls = links

            base64_images_list = url_to_base64(urls)

            message = attribute_generation_prompt(user_prompt,base64_images_list)

            attributes, token_amount=chat_with_model(message)
            final_output = parser.parse(attributes)
            fetched_attributes = dict(final_output)
            fetched_attributes = {key.replace('__', ' '): value for key, value in fetched_attributes.items()}
            
            image_attribute_fetch_dictionary[sku]=fetched_attributes
    except Exception as e:
        print(e)
    return(image_attribute_fetch_dictionary)

