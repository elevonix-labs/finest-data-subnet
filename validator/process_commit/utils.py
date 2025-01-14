def extract_commit(input:str)-> str:
    # Split the string only at the first occurrence of ':'

    url = input.split(':')[-1]

    return url