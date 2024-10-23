from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from preprocessing.preprocessing_functions import image_attribute_fetch_dictionary_func
import json
from json import JSONDecodeError

@api_view(['POST'])
def attribute_fetch(request):
    try:
        # Get JSON data from the request
        json_data = request.data
        try:
            json_data = json.loads(json_data)
        except Exception as e:
            json_data = json_data
        # print("json_data",json_data)

        # Process each SKU in the json_data
        results = []
        for sku, data in json_data.items():
            cat = data.get('category')
            sub_category = data.get('sub_category')
            images_links = data.get('images_links')
            df_dict = data.get('df_dict')
            prompt = data.get('prompt')
            image_angle = data.get('image_angle')
            

            # Generate attributes using the image_attribute_fetch_dictionary_func
            image_attribute_fetch_dictionary = image_attribute_fetch_dictionary_func(
                cat, sub_category, {sku : images_links}, df_dict, prompt, image_angle
            )
            
            result = {
                'Seller SKU ID': sku,
                'attributes': image_attribute_fetch_dictionary[sku]
            }
            results.append(result)

        return Response(results)

    except Exception as e:
        print(e)
        return Response({'error': str(e)}, status=400)