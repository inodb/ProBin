from itertools import product
from collections import Counter
import sys
import os
class DNA(object):
    BASE_COMPLEMENT = {"A":"T","T":"A","G":"C","C":"G"}
    kmer_hash={}
    kmer_len = None
    @classmethod
    def generate_kmer_hash(cls,kmer_len):
        if cls.kmer_hash:
            raise Exception("Already initialized, can't change during execution")
        cls.kmer_len = kmer_len
        counter = 0
        for kmer in product("ATGC",repeat=cls.kmer_len):
            if kmer not in cls.kmer_hash:
                kmer = ''.join(kmer)
                cls.kmer_hash[kmer] = counter
                rev_compl = ''.join([cls.BASE_COMPLEMENT[x] for x in reversed(kmer)])
                cls.kmer_hash[rev_compl] = counter
                counter += 1
        cls.kmer_hash_count = counter
    
    def __init__(self,id,seq):
        if not self.kmer_len:
            raise Exception("Please run DNA.generate_kmer_hash(kmer_len) first.")
        self.id = id
        self.seq = seq.upper().split("N")
        self.signature = self.calculate_signature()
        
    def calculate_signature(self):
        signature = Counter()
        for fragment in self.seq:
            if len(fragment) < self.kmer_len:
                continue
            (indexes,not_in_hash) = self._get_kmer_indexes(fragment) #[self.kmer_hash[fragment[i:i+self.kmer_len]] for i in xrange(len(fragment) - (self.kmer_len-1)) if fragment[i:i+self.kmer_len] in self.kmer_hash]
            signature.update(indexes)
        if not_in_hash:
            sys.stderr.write("Sequence id: %s, skipped %i kmers that were not in dictionary%s" % (self.id,not_in_hash,os.linesep)) 
        return signature
    def _get_kmer_indexes(self,seq):
        indexes = []
        not_in_hash = 0
        for i in xrange(len(seq) - (self.kmer_len - 1)):
            if seq[i:i+self.kmer_len] in self.kmer_hash:
                indexes.append(self.kmer_hash[seq[i:i+self.kmer_len]])
            else:
                not_in_hash += 1
        return (indexes,not_in_hash)