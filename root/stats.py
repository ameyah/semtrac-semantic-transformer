'''
Basic statistics on classification.

@author: Rafa
'''

from database import PwdDb
from tagset_conversion import TagsetConverter

def main():
    
    db = PwdDb()
    tc = TagsetConverter() # assumes the pwds are pos-tagged using Brown tags
    
    pos_dist    = dict() 
    wn_pos_dist = dict()
    
    fragments_total = 0  # number of words
    pos_total       = 0  # number of pos-tagged words
    wn_verbs_total  = 0  # number of verbs that are found in wordnet
    wn_nouns_total  = 0  # number of verbs that are found in wordnet
        
    while (db.hasNext()):
        words = db.nextPwd() # list of Words
        fragments_total += len(words)
        
        for w in words:
            if w.pos is None :
                continue
            pos_total += 1
            
            if w.pos in pos_dist :
                pos_dist[w.pos] += 1
            else : 
                pos_dist[w.pos] = 1
            
            wn_pos = tc.brownToWordNet(w.pos)
            
            if wn_pos in wn_pos_dist :
                wn_pos_dist[wn_pos] += 1
            else : 
                wn_pos_dist[wn_pos] = 1
                
            if w.synsets is not None:
                if wn_pos == 'v' :
                    wn_verbs_total += 1
                elif wn_pos == 'n' :
                    wn_nouns_total += 1
        
    db.finish()
    
    # convert to list of tuples so we can sort it by value
    pos_dist = pos_dist.items()
    pos_dist = sorted(pos_dist, key = lambda entry: entry[1], reverse=True)
    
    print "Total number of fragments: {}".format(fragments_total)
    print 'of which {} are POS tagged words ({}%)'.format(pos_total, float(pos_total)*100/fragments_total)
    print '\nPOS distribution (Brown tagset):\n'
    for k, v in pos_dist:
        print "{}\t{}".format(k, v)
    print '\nPOS distribution (WordNet tagset):\n', wn_pos_dist     
    print '\n{} verbs found in WordNet ({}% of verbs)'.format(wn_verbs_total, float(wn_verbs_total)*100/wn_pos_dist['v'])
    print '\n{} nouns found in WordNet ({}% of nouns)'.format(wn_nouns_total, float(wn_nouns_total)*100/wn_pos_dist['n'])
    
    return 0
    
if __name__ == "__main__":
    main()

    

