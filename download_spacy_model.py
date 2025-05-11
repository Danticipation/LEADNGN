import spacy
import sys

print('SpaCy version:', spacy.__version__)

try:
    nlp = spacy.load('en_core_web_sm')
    print('Language model loaded successfully')
except:
    print('Language model not found, downloading...')
    spacy.cli.download('en_core_web_sm')
    print('Download completed')