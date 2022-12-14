# PIXL Report De-identifier

Reports are de-identified based on a combined [Presido](https://microsoft.github.io/presidio/) +
[regex](https://en.wikipedia.org/wiki/Regular_expression) approach and aims to 
remove all absolute identifiers (e.g. NHS number), almost all >99% full names
and most dates/partial names. 

### Notes

- Linebreaks are not always preserved and some partial text overlaps of masks exist
- Presido identifies nouns as names on occasion


***

### Local installation

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_lg  # Download spacy language model
```
