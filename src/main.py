import spacy
from spacy import displacy

with open("../data/dodisTestText.txt","r") as f:
    text=f.read().replace("\n\n", " ").replace("\n", " ")

nlp = spacy.load("de_core_news_sm")

doc = nlp(text)

html = displacy.render(doc, style="ent")

with open ("data_vis.html", "w") as f:
    f.write(html)