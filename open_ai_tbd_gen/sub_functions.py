def key_value_pair_modified(incoming_sheet_with_mandate_columns):

    Column_key_value_pair=dict(incoming_sheet_with_mandate_columns.iloc[0])

    #transforming the data to a organised dictionary.
    key_value_pair_modified = {}
    for key, value in Column_key_value_pair.items():
        if key.startswith('Unnamed:'):
            new_key = 'Unnamed'
        else:
            new_key = key.split('.')[0]
        
        if new_key in key_value_pair_modified:
            if isinstance(key_value_pair_modified[new_key], list):
                key_value_pair_modified[new_key].append(value)
            else:
                key_value_pair_modified[new_key] = [key_value_pair_modified[new_key], value]
        else:
            key_value_pair_modified[new_key] = value
    return (key_value_pair_modified)