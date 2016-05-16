"""
Specialized Tree and TreeNode for WordNet.
   
Created on 2013-03-25
@author: rafa
"""

from nltk.corpus import wordnet as wn 
from default_tree import DefaultTree, DefaultTreeNode
from collections import deque

class WordNetTreeNode(DefaultTreeNode):
    
    # a counter for ids. Everytime a node is created, next_id is assigned to it
    # and incremented.
    next_id = 0
    
    def __init__(self, key, parent=None):
        DefaultTreeNode.__init__(self, key)
        
        self.cut = False  # True if this node belongs to a tree cut
        self.parent = parent
        
        # a unique identifier is necessary, since many nodes are duplicated
        # and preserve the same name
        self.id = WordNetTreeNode.next_id
        WordNetTreeNode.next_id += 1  

    def wrap(self):
        """ Returns a representation of this node (including all children)
        as a single object, JSON-style.
        """
        children = list()
        for child in self.children():
            children.append(child.wrap())
        if len(children) == 0:
            return {'key': self.key, 'value': self.value, 'id': self.id}
        else:
            return {'key': self.key, 'value': self.value,
                    'entropy': self._entropy, 'id': self.id, 'children': children}

    def path(self):
        """ Returns the path to the root based on the parent attribute."""
        path = list()
        
        curr = self
        while curr:
            path.insert(0, curr)
            curr = curr.parent
        
        return path
    
    def create_node(self, key):
        return WordNetTreeNode(key, self)


class WordNetTree(DefaultTree):
    """
    A POS-specific tree representation of WordNet.

    1. Nodes with multiple parents are duplicated
    2. Senses are separated from semantic class, i.e.,
       for each non-leaf node, a node with prefix 's' 
       is appended as first child representing its sense.
       So all leaves represent senses, all internal nodes
       represent classes.
       For example:
           person.n.01
               s.person.n.01
               cripple.n.01
                   humpback.n.02
               faller.n.02                 
               hater.n.01
    """
    
    def __init__(self, pos):
        """ Loads the WordNet tree for a given part-of-speech.
           'entity.n.01' is the root for nouns; otherwise, creates an artificial
           root named 'root' whose children are all the root nodes (the verbs ontology
           has several roots).
            
        """
        self.pos = pos
        self.load(pos)

    def load(self, pos):
        if pos == 'n':
            roots = wn.synsets('entity')
        else:
            roots = [s for s in wn.all_synsets(pos) if len(s.hypernyms()) == 0]
        
        self.root = WordNetTreeNode('root')
        
        for synset in roots:
            self.__append_synset(synset, self.root)


    def __append_synset(self, synset, root):
        """Appends the whole  subtree rooted at a  synset to a  root. 
        Visits all descendant synsets in a DFS fashion (iteratively), 
        creating a WordNetTreeNode for each synset.
        If the synset is not a leaf, creates a child representing its 
        sense, with 's.' as a prefix, e.g.,
            person.n.01
                s.person.n.01
                .
                .
        The measure above preserves the constraint that leaves should
        represent senses and internal nodes should represent classes.
        """
        stack = deque()
        stack.append((synset, root))

        while len(stack):
            syn, parent = stack.pop()
            syn_node = parent.insert(syn.name)

            hyponyms = syn.hyponyms()
            
            # if not leaf, insert a child representing the sense 
            if len(hyponyms) > 0:
                syn_node.insert('s.'+syn.name)
            
            for hypo in syn.hyponyms():
                stack.append((hypo, syn_node))

        
#    def __append_synset(self, synset, parent):
#        """Recursive method to a append synset (and all its children) to a parent. 
#        Given a parent node, creates a node for the informed synset 
#        and inserts it as a child.
#        If the synset is not a leaf, creates its first child representing
#        its sense, with 's.' as a prefix, e.g.,
#            person.n.01
#                s.person.n.01
#                .
#                .
#        """
#        node = parent.insert(synset.name)
#        hyponyms = synset.hyponyms()
#        
#        # if not leaf, insert a child representing the sense 
#        if len(hyponyms) > 0:
#            node.insert('s.'+synset.name)
#        
#        for h in hyponyms:
#            self.__append_synset(h, node)
            
    def increment_synset(self, synset, freq=1):
        paths = synset.hypernym_paths()
        
        if len(paths) > 1:
            freq = float(freq) / len(paths)
        
        # multiplies the sense if has more than one parent 
        for i, path in enumerate(paths):
            path = [s.name for s in path]
            if len(synset.hyponyms()) > 0:  # internal node
                path.append('s.' + path[-1])
            self.insert(path, freq)
            
            
if __name__ == '__main__':
    pass
