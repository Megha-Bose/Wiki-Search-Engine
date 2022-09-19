import os
import sys
import time
import math
import re
from typing import DefaultDict
import Stemmer
import bisect
from tokenize import *
from collections import defaultdict

field_acronyms = ['b', 'c', 'i', 'l', 'r', 't']
punctuation = ".,|+-@~`:;?()*\"'=\\&/<>[]{}#!%^$ "
total_num_docs = 0
out_file = None

stemmer = Stemmer.Stemmer('english')
check_stopword = defaultdict(int)

f = open('secondary_index.txt', 'r')
secondary_indexes = f.readlines()
f.close()

def get_total_doc_num():
    global total_num_docs
    with open('my_stat.txt', 'r') as f:
        for val in f:
            total_num_docs = int(val.strip("\n"))
    print(total_num_docs)

with open('stopwords.txt', 'r') as f:
    for stopword in f:
        stopword = stopword.strip(' ').strip("\n")
        check_stopword[stopword] = 1


def tokenize(content):
    return re.findall(
        "[A-Z]{2,}(?![a-z])|[A-Z][a-z]+(?=[A-Z])|[\'\w\-]+", content)


def stemWords(content):
    return stemmer.stemWords(content)


def is_noise(content):
    global punctuation
    return content in punctuation or len(content) <= 1 or len(content) >= 30


def removeNoise(content):
    return [word for word in content if check_stopword[word] != 1 and not is_noise(word)]


# Tokenizing, removing stopwords, stemming.
def NLProcessing(content):
    return stemWords(removeNoise(tokenize(str(content))))


with open('stopwords.txt', 'r') as f:
    for stopword in f:
        stopword = stopword.strip(' ').strip("\n")
        check_stopword[stopword] = 1


def get_title(doc_num):
    file = open("titles/titles_" + str(doc_num // 2000) + '.txt')
    title = file.readlines()[doc_num % 2000].strip('\n')
    return title


def get_posting_list(term):
    pos = bisect.bisect(secondary_indexes, term + '\n') - 1
    print("Index File No.: ", pos)
    if pos > 0:
        f = open('indexes/index_' + str(pos) + '.txt', 'r')
        line = f.readline().strip('\n')
        while line:
            words = line.split(":")
            if term in words[0]:
                return words[1]
            line = f.readline().strip('\n')
    return ""


def rank(inp_terms, fields, type):
    global total_num_docs
    terms = []
    if type == "field":
        terms = inp_terms
        for i in range(0, len(terms)):
            terms[i] = str(terms[i]) + "-" + str(fields[i])
    else:
        for inp_term in inp_terms:
            for fld in field_acronyms:
                terms.append(inp_term + "-" + fld)
                fields.append(fld)
    
    scores = defaultdict(float)
    num_terms = len(terms)
    term_occurences = defaultdict(int)

    for i in range(0, len(terms)):
        print("\n----------")
        postlist = get_posting_list(terms[i])
        print("postlist: ", postlist)
        if len(postlist) > 0:
            tfs = []
            doc_nums = []
            docs = postlist.split("d")[1:]
            for doc in docs:
                val = doc.split("-")
                doc_nums.append(val[0])
                tfs.append(int(val[1].split("|")[0]))
            df = len(doc_nums)
            idf = math.log2(total_num_docs/(df + 1))
            print("df: ", df)
            print("term: ", terms[i])
            print("docs: ", doc_nums)
            print("tfs: ", tfs)
            for j in range(0, len(doc_nums)):
                doc_num = int(doc_nums[j])
                tf = tfs[j]
                weight = 0
                if fields[i] == 't':
                    weight = 100
                elif fields[i] == 'i':
                    weight = 50
                elif fields[i] == 'c':
                    weight = 30
                elif fields[i] == 'b':
                    weight = 30
                elif fields[i] == 'l':
                    weight = 10
                elif fields[i] == 'r':
                    weight = 10
                scores[doc_num] += (weight * math.log2(tf + 1) * idf)
                term_occurences[doc_num] += 1
    results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    print_text = ""
    max_results = 10
    count = 0
    i = 0
    while i < len(results):
        if term_occurences[results[i][0]] > num_terms / 1000:
            print_text += (str(results[i][0]) + ', ' + get_title(results[i][0]) + "\n")
            # print(scores[results[i][0]])
            count += 1
            if count >= max_results:
                break
        i+=1
    return print_text


def search_field_query(query):
    words = re.findall(r'[b|c|i|l|r|t]:([^:]*)(?!\S)', query)
    temp = re.findall(r'([b|c|i|l|r|t]):', query)
    tokens = []
    fields = []
    for i in range(len(words)):
        for word in words[i].split():
            tks = NLProcessing(word)
            for tkn in tks:
                tokens.append(tkn)
                fields.append(temp[i])
    terms = NLProcessing(tokens)
    return rank(terms, fields, 'field')


def search_simple_query(query):
    terms = NLProcessing(query)
    return rank(terms, [], 'simple')


if __name__ == "__main__":
    get_total_doc_num()
    query_file_name = sys.argv[1]
    query_file = open(query_file_name, 'r')
    queries = query_file.readlines()
    out_file = open('queries_op.txt', 'w')
    for query in queries:
        query = query.lower()
        start = time.time()
        out = ""
        if ("t:" in query or "b:" in query or "i:" in query or "c:" in query or "l:" in query or "r:" in query):
            out = search_field_query(str(query))
        else:
            out = search_simple_query(str(query))
            query = query + "\n"
        # out_file.write(query)
        out_file.write(out)
        end = time.time()
        out_file.write(str(round(end - start, 2)) + '\n\n')
    query_file.close()
    out_file.close()
