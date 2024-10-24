from openai import OpenAI
import pandas as pd
import requests
import base64
# from pydantic import BaseModel, Field, field_validator, FieldValidationInfo
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from dotenv import load_dotenv
import logging

load_dotenv()
client = OpenAI()

def create_model_class_def(attributes_dict: dict, catgory: str = None, sub_category: str = None, sku: str = None):
    logging.basicConfig(
        filename=r'E:\QuickUp_backend_V1\QuickUp_DRF\log\log.txt',
        level=logging.ERROR,
        format='%(asctime)s - %(message)s',
        datefmt='%d-%m-%Y %H:%M'
    )
    class_def = """
class ClothingAttributes(BaseModel):
"""
    for attr_name, values in attributes_dict.items():
        attr_info = attributes_dict[attr_name]
        values = [x for x in list(attr_info['values']) if not pd.isna(x)]
        values.append('')
        # values = values[~np.isnan(values)]
        values = repr(tuple(values))
        description = repr(attr_info['description'])
        attr_name = attr_name.replace(' ','__')
        print('attr_name: ', attr_name)
        print('values: ', values)
        # attr_name = attr_name.replace('-','_')
        class_def += f"    {attr_name}: Literal[{values}] = Field(..., description={description})\n"
    
    class_def += "\n"

    for attr_name, values in attributes_dict.items():
        if attr_name in attributes_dict:
            attr_info = attributes_dict[attr_name]
            attr_name = attr_name.replace(' ','__')
            # attr_name = attr_name.replace('-','_')
            values = attr_info.get('values', [])
            if values:
                values = list(values)
                values.append('')
                # values = values[~np.isnan(values)]
                values_repr = repr(values)
                validator_code = (
                    f"    @field_validator('{attr_name}', mode='before')\n"
                    f"    def validate_{attr_name}(cls, value: Any, info: FieldValidationInfo) -> Any:\n"
                    f"        if value not in {values_repr}:\n"
                    f"            logging.error(f'Invalid value for Category: {catgory}, {attr_name}: {{value}}, SKU: {sku}')\n"
                    f"            print(f'Invalid value for Category: {catgory}, {attr_name}: {{value}}, SKU: {sku}')\n"
                    f"            return ''\n"
                    f"        return value\n"
                )
                class_def += validator_code
                print('class_def: ', class_def)
            else:
                print(f"Validation rule for {attr_name} not added because the 'values' list is empty")
        else:
            print(f"Validation rule for {attr_name} not added because it is not in included attributes")
    namespace = {}
    try:
        exec(class_def, globals(), namespace)
        return namespace['ClothingAttributes']
    except Exception as e:
        print(f"Error executing class definition: {e}")
        return None

def attribute_prompt_parser(prompt, clothing_attributes_class):
    try:
        parser = PydanticOutputParser(pydantic_object=clothing_attributes_class)
        init_prompt = PromptTemplate(template=prompt, input_variables=[],
                                     partial_variables={'format_instructions': parser.get_format_instructions()})
        formatted_prompt = init_prompt.format_prompt().to_string()
        return formatted_prompt, parser
    except Exception as e:
        print(f'Error in attribute_prompt_parser: {e}')
        return None, None

def url_to_base64(path_or_url_list: list):
    # url_list = []
    # [url_list.append(url) for url in path_or_url_list]
    # print(path_or_url_list)
    image_list = []
    for path_or_url in path_or_url_list:
        if path_or_url.startswith("http"):
            image = requests.get(path_or_url)
            if image.status_code == 200:
                image_list.append(base64.b64encode(image.content).decode('utf-8'))

            else:
                print(f"Error in fetching the image from {path_or_url}")
        else:
            with open(path_or_url, "rb") as img_file:
                image_data = img_file.read()
            image_list.append(base64.b64encode(image_data).decode('utf-8'))
    
    return image_list

def attribute_generation_prompt(user_prompt,base_64_image_list):
    message=[
              {"role": "system", "content": "You are a helpful assistant that helps users in describing what's inside the images to the best of your abilities."},
              {"role": "user", "content": [
                                           {"type": "text", "text": user_prompt},                                         
                                          ]}
                ]
    
    for image in base_64_image_list:
        message[1]["content"].append({"type": "image_url", "image_url": {"url": f'data:image/jpeg;base64,{image}', 'detail': "low"}})

    return message

def chat_with_model(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=message,
            temperature=0,
        )
        total_token = response.usage.total_tokens
        output = response.choices[0].message.content
        print(output)
        return output, total_token

    except Exception as e:
        print(f"Error in attribute_retrieval:{e}")
        return None, 0