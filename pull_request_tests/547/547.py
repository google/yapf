_schema = [
    ('uuid', {'field_type': 'STRING'}),
    ('ingredient_line', {'field_type': 'STRING'}),
    ('item_name', {'field_type': 'STRING'}),
    ('query', {'field_type': 'STRING'}),
    ('item_name_seq', {'field_type': 'INTEGER', 'mode': 'REPEATED'}),
    ('query_seq', {'field_type': 'INTEGER', 'mode': 'REPEATED'}),
    ('relevance', {'field_type': 'FLOAT'}),
    ('fold', {'field_type': 'INTEGER'}),
    ('params', {'field_type': 'STRING'}),
    ('timestamp', {'field_type': 'DATETIME'})
]
