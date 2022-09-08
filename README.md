# Wikipedia-Search-Engine
Creating an inverted index from Wikipedia dump and using TF-IDF score to retrieve relevant documents for search queries.It also supports field queries for fields Title, Infobox, Body, Category, Links and References.

## Run:
```
bash index.sh <path_to_wiki_dump> <path_to_inverted_index> <path_to_stat_file>
bash search.sh <path_to_inverted_index> <path_to_file_containing_queries>
```

## Directories and Files:

- **indexes directory**: Contains split inverted index.
- **intermediates directory**: Used for merging indices.
- **titles directory**: Contains titles split into smaller files.
- **index.py**: Creating primary and secondary indices.
- **search.py**: Searching field and plain queries.
- **final_index.txt**: File storing merged indices.
- **secondary_index.txt**: First token of each index file.
- **queries.txt**: Contains input search queries.
- **stopwords.txt**: Contains english stopwords.

## Points:

- Tokens are sorted for optmised merging of index files.
- The inverted index file is split into smaller files for faster search.
- First tokens of each such smaller index file is stored for easier access during search since the tokens are sorted.
- Titles of the documents are split into smaller file blocks sequentially which can be easily accessed by calculating the offset.
