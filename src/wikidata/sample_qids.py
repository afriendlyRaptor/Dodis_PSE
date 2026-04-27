
# cat dodis_wikidata.db > db_dump.txt
# grep -a -o 'Q[0-9]\+' db_dump.txt > qid_list.txt


import random


def sample_qid_list(filepath:str,samplesize):
    with open(filepath) as f:
        qids = {str(line.strip()) for line in f if line.strip()}  # set = unique
        
    if len(qids) == 0:
        raise ValueError("The file contains no QIDs.") 


    sample = random.sample(list(qids), int(samplesize))
    print(sample)
    return sample
    
