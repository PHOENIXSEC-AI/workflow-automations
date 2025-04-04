
from core.config import app_config
from core.utils.tokenization import get_tokenizer,count_tokens


def _load_file(file_pth:str) -> str:
    with open(file_pth, 'r') as file:
        content = file.read()
    return content
def main(input_text_file_pth:str):
    tokenizer = get_tokenizer(app_config.DEFAULT_TOKENIZER)

    file_content = _load_file(input_text_file_pth)
    
    tokens_count = count_tokens(file_content)
    
    return tokens_count

if __name__ == "__main__":
    main('docs/standards/owasp/owasp_asvs.txt')