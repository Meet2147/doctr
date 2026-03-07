from pprint import pprint
from doctr import index_document
idx = index_document("src/doctr/algo.pdf", summary_max_chars=1500)
data = idx.to_pageindex_dict()  # full summaries
pprint(data)