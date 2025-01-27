def extract_commit(input:str)-> str:
    # Split the string only at the first occurrence of ':'

    hf_url, hash = input.split(':')

    return hf_url, hash