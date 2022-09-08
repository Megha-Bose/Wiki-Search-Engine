import os
import sys
import time
import re
import Stemmer
import xml.sax
import math
from bz2file import BZ2File
from tokenize import *
from collections import defaultdict

curr_doc_count = 0
title_file_no = 0
curr_file_num = 0
total_num_tokens = 0
num_index_tokens = 0
num_index_files = 0
num_fields = 6
index = defaultdict(dict)
page_titles = []

field_acronyms = ['b', 'c', 'i', 'l', 'r', 't']
punctuation = ".,|+-@~`:;?()*\"'=\\&/<>[]{}#!%^$ "

stemmer = Stemmer.Stemmer('english')

check_stopword = defaultdict(int)

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
    return stemWords(removeNoise(tokenize(content)))


# Class handling tokenization, field querying, indexing, etc. of the document content.
class WikiDoc(object):
    def __init__(self, doc_num, doc_id, title, text):
        self.doc_num = doc_num
        self.doc_id = doc_id

        # Case folding.
        self.title = title.lower()
        self.text = text.lower()

        self.title_words = []
        self.body_words = []
        self.infobox_words = []
        self.category_words = []
        self.link_words = []
        self.reference_words = []
        self.processContent()

    # Creating inverted index for the document.
    def processContent(self):
        global total_num_tokens
        total_num_tokens += len(tokenize(self.title + " " + self.text))
        self.title_words = NLProcessing(self.title)
        self.title_words = [re.sub(r"(^[^\w]+)|([^\w]+$)", "", x)
                            for x in self.title_words]
        self.splitContent()

    # General structure of xml code for a wiki page:
    # 1. Initial body section
    # 2. Infobox section
    # 3. Descriptive body section (containing references too)
    # 4. External links section
    # 5. Separate references section
    # 6. Categories section

    # Splitting into Body - Infobox - External Links - References - Category.
    def splitContent(self):
        infobox_start, infobox_end = self.setInfoboxFieldContent()
        cat_start = self.setCategoryFieldContent(infobox_end)
        ref_start = self.setReferenceFieldContent(infobox_end, cat_start)
        links_start = self.setLinkFieldContent(infobox_end, ref_start)
        self.setBodyFieldContent(infobox_start, infobox_end, links_start)

    # Locate and set words from infobox content.
    def setInfoboxFieldContent(self):
        infobox_tag_start = 0
        infobox_tag_end = 0
        infobox_tag_instance = re.search("\{\{\s*infobox", self.text)
        if infobox_tag_instance != None:
            infobox_tag_start = infobox_tag_instance.start()
            infobox_tag_end = infobox_tag_start + 1
            open_braces = 0
            start_flag = True
            for val in self.text[infobox_tag_start:]:
                if val == '{':
                    open_braces += 1
                elif val == '}':
                    open_braces -= 1
                if open_braces == 0:
                    if start_flag:
                        start_flag = False
                    else:
                        break
                infobox_tag_end += 1
            self.infobox_words = NLProcessing(re.sub("\{\{\s*infobox", " ",
                                                     self.text[infobox_tag_start: infobox_tag_end], re.IGNORECASE))
            self.infobox_words = [
                re.sub(r"(^[^\w]+)|([^\w]+$)", "", x) for x in self.infobox_words]
        return infobox_tag_start, infobox_tag_end

    # Set words from categories.
    def setCategoryFieldContent(self, st):
        cat_start = len(self.text)
        category_tag_instance = re.search(
            "\[\[\s*category\s*:", self.text[st:])
        if category_tag_instance != None:
            cat_start = category_tag_instance.start()
            self.category_words = NLProcessing(
                re.sub("\[\[\s*category\s*:", " ", self.text[cat_start:], re.IGNORECASE))
            self.category_words = [
                re.sub(r"(^[^\w]+)|([^\w]+$)", "", x) for x in self.category_words]
        return cat_start

    # Set words from all references.
    def setReferenceFieldContent(self, st, en):
        ref_start = en
        ref_tag_instance = re.search(
            "={2,3}\s*references\s*={2,3}", self.text[st:en])
        if ref_tag_instance != None:
            ref_start = ref_tag_instance.start()
            self.reference_words = NLProcessing(
                re.sub("={2,3}\s*references\s*={2,3}", " ", self.text[ref_start:en], re.IGNORECASE))
            self.reference_words = [
                re.sub(r"(^[^\w]+)|([^\w]+$)", "", x) for x in self.reference_words]

    # Set words from external links.
    def setLinkFieldContent(self, st, en):
        link_start = en
        link_tag_instance = re.search(
            "={2,3}\s*external\s*links\s*={2,3}", self.text[st:en])
        if link_tag_instance != None:
            link_start = link_tag_instance.start()
            self.link_words = NLProcessing(
                re.sub("={2,3}\s*external\s*links\s*={2,3}", " ", self.text[link_start:en], re.IGNORECASE))
            self.link_words = [re.sub(r"(^[^\w]+)|([^\w]+$)", "", x)
                               for x in self.link_words]
        return link_start

    # Set words from body content.
    def setBodyFieldContent(self, first_chunk_end, second_chunk_start, second_chunk_end):
        self.body_words = NLProcessing(
            re.sub(r'\{\{.*\}\}', r' ', self.text[:first_chunk_end] +
                   "\n" + self.text[second_chunk_start:second_chunk_end]))
        self.body_words = [re.sub(r"(^[^\w]+)|([^\w]+$)", "", x)
                           for x in self.body_words]


# XML parser content handler class and index creator for the wikidump.
class WikiDocHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.tag = ""
        self.doc_num = 0
        self.doc_id = ""
        self.doc_flag = False
        self.title = ""
        self.text = ""

    def updateIndex(self, doc):
        global index, inv_index_out_path, field_acronyms, curr_file_num, num_fields, page_titles, title_file_no, curr_doc_count

        # Updating word count for each field in the document they appeared in.
        for word in doc.title_words:
            try:
                index[word][doc.doc_num]
            except:
                index[word][doc.doc_num] = [0] * num_fields
            index[word][doc.doc_num][0] += 1
        for word in doc.body_words:
            try:
                index[word][doc.doc_num]
            except:
                index[word][doc.doc_num] = [0] * num_fields
            index[word][doc.doc_num][1] += 1
        for word in doc.infobox_words:
            try:
                index[word][doc.doc_num]
            except:
                index[word][doc.doc_num] = [0] * num_fields
            index[word][doc.doc_num][2] += 1
        for word in doc.category_words:
            try:
                index[word][doc.doc_num]
            except:
                index[word][doc.doc_num] = [0] * num_fields
            index[word][doc.doc_num][3] += 1
        for word in doc.link_words:
            try:
                index[word][doc.doc_num]
            except:
                index[word][doc.doc_num] = [0] * num_fields
            index[word][doc.doc_num][4] += 1
        for word in doc.reference_words:
            try:
                index[word][doc.doc_num]
            except:
                index[word][doc.doc_num] = [0] * num_fields
            index[word][doc.doc_num][5] += 1

        # sample --- sachin-t:d1-1|d5-1
        if curr_doc_count % 20000 == 0 and curr_doc_count:
            curr_file_num += 1
            f = open(inv_index_out_path + "/intermediates/index_file_" +
                     str(curr_file_num) + ".txt", "w+")
            title_f = open(f'titles/titles_{title_file_no}.txt', 'w+')
            for page_title in page_titles:
                title_f.write(page_title)
            title_file_no += 1
            page_titles.clear()
            title_f.close()
            word_list = sorted(index.keys())
            for word in (word_list):
                for i in range(len(field_acronyms)):
                    line = ""
                    line = word + "-" + field_acronyms[i] + ":"
                    docs = index[word]
                    for doc in (sorted(docs.keys())):
                        line = line + "d" + str(doc) + "-"
                        if index[word][doc][i]:
                            line = line + str(index[word][doc][i])
                            line = line + "|"
                        else:
                            line = ""
                    if len(line) > 0 and line[-1] == "|":
                        line = line[:-1]
                    f.write(line)
                    if len(line) > 0:
                        f.write("\n")
            f.close()
            index = defaultdict(dict)

    def reset(self):
        self.tag = ""
        self.doc_num = 0
        self.doc_id = ""
        self.doc_flag = False
        self.title = ""
        self.text = ""

    def startElement(self, tag, attrs):
        self.tag = tag

    def endElement(self, tag):
        global curr_doc_count, page_titles
        if (tag == "page"):
            doc = WikiDoc(curr_doc_count, self.doc_id, self.title, self.text)
            page_titles.append(self.title.lower())
            self.updateIndex(doc)
            curr_doc_count += 1
            print(curr_doc_count, end="\r")
            self.reset()

    def characters(self, content):
        if self.tag == "id" and self.doc_flag == False:
            self.doc_id = content
            self.doc_flag = True
        elif self.tag == "title":
            self.title += content
        elif self.tag == "text":
            self.text += content


def writeIndexStatFile():
    global total_num_tokens, num_index_tokens, index, curr_doc_count, num_index_files
    f = open("my_stat.txt", "w+")
    f.write(str(total_num_tokens) + "\n" + str(num_index_tokens) + "\n" + str(curr_doc_count))
    f.close()
    # index size in GB (for e.g. 17.36) -> size of inv_index_out_path + '/final_index' + '.txt'
    # number of files in which the inverted index is split (for e.g. 26)
    # number of tokens in the inverted index (for e.g. 872985644)
    index_file_size = os.path.getsize(inv_index_out_path + '/final_index' + '.txt')
    p = math.pow(1024, 3)
    s = round(index_file_size / p, 2)
    f = open(inv_index_stat_path + "/stats.txt", "w+")
    f.write(str(s) + "\n" + str(num_index_files) + "\n" + str(num_index_tokens))
    f.close()


# sample --- sachin-t:d1-1|d5-1
def merge2Files(left_id, right_id):
    f1 = open(inv_index_out_path + '/intermediates/index_file_' +
              str(left_id) + '.txt', 'r')
    f2 = open(inv_index_out_path + '/intermediates/index_file_' +
              str(right_id) + '.txt', 'r')

    tmp = open(inv_index_out_path + '/intermediates/tmp_index_file.txt', 'w+')

    print("Merging " + str(left_id) + " and " + str(right_id))

    l1 = f1.readline()
    l2 = f2.readline()

    while (l1 and l2):
        while len(l1.split(':')) <= 1:
            l1 = f1.readline()
        line1 = l1.split(':')
        key1 = line1[0]
        postlist1 = line1[1]
        while len(l2.split(':')) <= 1:
            l2 = f2.readline()
        line2 = l2.split(':')
        key2 = line2[0]
        postlist2 = line2[1]

        if key1 < key2:
            tmp.write(l1)
            l1 = f1.readline()
        elif key1 > key2:
            tmp.write(l2)
            l2 = f2.readline()
        else:
            tmp.write(key1 + ':' + postlist1.strip() + "|" + postlist2)
            l1 = f1.readline()
            l2 = f2.readline()

    while (l1):
        tmp.write(l1)
        l1 = f1.readline()
    while (l2):
        tmp.write(l2)
        l2 = f2.readline()

    f1.close()
    f2.close()
    tmp.close()

    # Remove children.
    os.remove(inv_index_out_path + '/intermediates/index_file_' +
              str(left_id) + '.txt')
    os.remove(inv_index_out_path + '/intermediates/index_file_' +
              str(right_id) + '.txt')
    # Update Parent.
    os.rename(inv_index_out_path + '/intermediates/tmp_index_file.txt',
              inv_index_out_path + '/intermediates/index_file_' + str(right_id // 2)+'.txt')


def mergeFiles():
    end = curr_file_num
    while end > 1:
        for i in range(1, end, 2):
            merge2Files(i, i + 1)
        if end % 2 == 1:
            os.rename(inv_index_out_path + '/intermediates/index_file_' + str(end) + '.txt',
                      inv_index_out_path + '/intermediates/index_file_' + str(end // 2 + 1) + '.txt')
        if end % 2 == 1:
            end = end // 2 + 1
        else:
            end = end // 2
    os.rename(inv_index_out_path + '/intermediates/index_file_1.txt', inv_index_out_path + '/final_index' + '.txt')


def main(wiki_xml_dump):
    global index, curr_file_num, title_file_no
    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_namespaces, 0)
    handler = WikiDocHandler()
    parser.setContentHandler(handler)
    parser.parse(wiki_xml_dump)
    if len(page_titles) > 0:
        title_f = open(f'titles/titles_{title_file_no}.txt', 'w+')
        for page_title in page_titles:
            title_f.write(page_title)
    if curr_doc_count % 20000 != 0:
        curr_file_num += 1
        f = open(inv_index_out_path + "/intermediates/index_file_" +
                 str(curr_file_num) + ".txt", "w+")
        word_list = sorted(index.keys())
        for word in (word_list):
            for i in range(len(field_acronyms)):
                line = ""
                line = word + "-" + field_acronyms[i] + ":"
                docs = index[word]
                for doc in (sorted(docs.keys())):
                    line = line + "d" + str(doc) + "-"
                    if index[word][doc][i]:
                        line = line + str(index[word][doc][i])
                        line = line + "|"
                    else:
                        line = ""
                if len(line) > 0 and line[-1] == "|":
                    line = line[:-1]
                f.write(line)
                if len(line) > 0:
                    f.write("\n")
        f.close()
    mergeFiles()

# Splitting the final index in smaller files and storing secondary index.
def split_final_index():
    global num_index_tokens, num_index_files
    num_final_index_lines = 0
    final_index = open(inv_index_out_path + '/final_index' + '.txt', 'r')
    secondary_index = open('secondary_index.txt', 'w+')
    line = final_index.readline().strip('\n')
    num_final_index_lines += 1
    lines = []
    last_word = ""
    while line:
        lines.append(line)
        curr_word = line.split(":")[0][:-2]
        if curr_word != last_word:
            last_word = curr_word
            num_index_tokens += 1
        if len(lines) % 10000 == 0:
            secondary_index.write(lines[0].split(":")[0] + '\n')
            fin_index = open('indexes/index_' + str(num_index_files) + '.txt', 'w+')
            for l in lines:
                fin_index.write(l + '\n')
            fin_index.close()
            num_index_files += 1
            lines = []
        line = final_index.readline().strip('\n')
        num_final_index_lines += 1
    # print(num_final_index_lines)
    # print(num_index_tokens)
    final_index.close()
    secondary_index.close()

wiki_dump_in_path = sys.argv[1]
inv_index_out_path = sys.argv[2]
inv_index_stat_path = sys.argv[3]

# 476811 pages - Phase 1
# 60M+ pages - Phase 2 
wiki_dump_in_path = "./enwiki-20220720-pages-articles-multistream15.xml-p15824603p17324602.bz2"

if __name__ == "__main__":
    path = os.path.join(inv_index_out_path, "intermediates")
    if not os.path.exists(path):
        os.mkdir(path)
    st = 0
    with BZ2File(wiki_dump_in_path) as wiki_xml_dump:
        st = time.time()
        main(wiki_xml_dump)
    # main("https://en.wikipedia.org/wiki/Special:Export/Bruce_Willis")
    end1 = time.time()
    print("Primary Indexing Done. Time taken: ", end1 - st)
    print('Creating Secondary Index...')
    split_final_index()
    end2 = time.time()
    print("Secondary Indexing done. Total time taken: ", end2 - st)
    writeIndexStatFile()