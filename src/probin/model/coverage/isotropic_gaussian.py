import scipy.stats
import numpy as np
from random import randint
from os import getpid
import sys

def pdf(x,mu,sigma):
    return scipy.stats.norm.pdf(x,loc=mu,scale=sigma).prod()

def log_probabilities(x,mu,sigma):
    return log_pdf(x,mu,sigma)

def fit_nonzero_parameters(x,**kwargs):
    return fit_parameters(x,**kwargs)

def log_pdf(x,mu,sigma):
    return np.log(scipy.stats.norm.pdf(x,loc=mu,scale=sigma)).sum()

def fit_parameters(x,expected_clustering=None):
    # Observe that mu will be 2-dimensional even though 
    # the number of clusters in expected_clustering is 1 or
    # if expected_clustering is undefined.

    N,L = x.shape # N: the number of contigs,L: the number of features
    if expected_clustering is None:
         # All contigs are 100% in this single cluster
        expected_clustering = np.ones((N,1))
    n = expected_clustering.sum(axis=0,keepdims=True)
    K = n.shape[1] # The number of clusters
    mu = np.dot(expected_clustering.T,x)
    mu /= n.T
    if N == 1:
        sigma = np.ones(K)
    else:
        sigma = np.zeros(K)
        for k in xrange(K):
            sigma[k] = np.array([np.dot(expected_clustering[i,k]*(x[i,:]-mu[k,:]),(x[i,:]-mu[k,:]).T) for i in xrange(N)]).sum()/n[0,k]

    return mu,sigma


def em(contigs, p, K, epsilon, max_iter, **kwargs):
    #N number of contigs
    #D number of features
    #K number of clusters
    N,D = contigs.shape
    
    #initialize with kmeans
    if not np.any(p):
        clustering,_, p = kmeans(contigs, p, K, epsilon, 2, **kwargs)
        
    else:
        print >> sys.stderr, "Not implemented for EM to start with fixed p (centroids)"
        sys.exit(-1)
    
    n = np.array([len(contigs[clustering==c]) for c in xrange(K)],dtype=float)
    
    log_qs = log_probabilities(contigs,p)
    max_log_qs = np.max(log_qs,axis=1,keepdims=True)
    log_qs = np.exp(log_qs - max_log_qs)

    prob_diff = np.inf
    prev_prob = -np.inf
    iteration = 0
    
    while(max_iter - iteration > 0 and prob_diff >= epsilon):
        #================================
        #Expectation
        #================================
        log_qs *= n
        z = log_qs / np.sum(log_qs,axis=1,keepdims=True)
        
        #================================
        #Maximization
        #================================
        p_new = fit_nonzero_parameters(contigs,z)
        
        #================================
        #Evaluation
        #================================
        log_qs = log_probabilities(contigs,p_new)
        max_log_qs = np.max(log_qs,axis=1,keepdims=True)
        log_qs = np.exp(log_qs - max_log_qs)

        curr_prob = np.sum((max_log_qs - np.log(np.sum(z*log_qs,axis=1,keepdims=True))))
        
        n = np.sum(z,axis=0,keepdims=True)

        prob_diff = curr_prob - prev_prob

        (curr_prob,prev_prob) = (prev_prob,curr_prob)
        (p,p_new) = (p_new,p)
        iteration += 1

    (curr_prob,prev_prob) = (prev_prob,curr_prob)
    print >> sys.stderr, "EM iterations: {0}, difference: {1}".format(iteration, prob_diff)
    if prob_diff < 0:
        print >> sys.stderr, "EM got worse, diff: {0}".format(prob_diff)
        (curr_prob,prev_prob) = (prev_prob,curr_prob)
        (p,p_new) = (p_new,p)
        
    #Get current clustering
    z = log_probabilities(contigs,p)
    #Find each contigs most likely cluster
    clustering = np.argmax(z,axis=1)
    return (clustering, curr_prob, p)

def kmeans(contigs, p, K, epsilon, max_iter, **kwargs):
    rs = np.random.RandomState(seed=randint(0,10000)+getpid())
    #N number of contigs
    #D number of features
    #K number of clusters
    N,D = contigs.shape
    #initialize centroids with random contigs
    sigma = np.zeros(K)
    if not np.any(p):
        ind = rs.choice(N,K,True)
        indx = np.arange(N)
        p = np.zeros((K,D))
        for i,centroid in enumerate(ind):
            p[i],sigma[K] = fit_nonzero_parameters(contigs[indx==centroid])
    p_new = np.zeros(p.shape)
    prev_prob = -np.inf
    prob_diff = np.inf
    iteration = 0
    
    while (prob_diff >= epsilon and max_iter-iteration > 0):
        #================================
        #Expectation
        #================================
        #Calculate responsibility
        z = log_pdf(contigs,p,sigma)
        #Find each contigs most likely cluster
        clustering_ind = np.argmax(z,axis=1)
        
        #================================
        #Maximization
        #================================
        # For ecah cluster
        for K_ind in xrange(K):
            #Gives boolean array with true for contigs belonging to cluster K
            clustering_K_ind = clustering_ind == K_ind
            #if empty, pick random contig to represent that clusters
            if not clustering_K_ind.any():
                new_centroid = np.arange(N) == rs.randint(0,N)
                p_new[K_ind] = fit_nonzero_parameters(contigs[new_centroid])
                print>>sys.stderr,"cluster {0} was empty in kmeans".format(K_ind)
            #Fit the contigs that belong to this cluster to the center
            else:
                p_new[K_ind] = fit_nonzero_parameters(contigs[clustering_K_ind])

        #================================
        #Evaluation
        #================================
        curr_prob = 0
        #for each cluster
        for K_ind in xrange(K):
            #create a boolean array representing that clusters so p[p_ind] is a 2D array (1xD)
            p_ind = np.arange(K) == K_ind
            #calculate log_probabilities of all contigs belonging to cluster k
            curr_prob += np.sum(log_probabilities(contigs[clustering_ind==K_ind],p_new[p_ind]))
        
        prob_diff = curr_prob - prev_prob 
        (curr_prob,prev_prob) = (prev_prob,curr_prob)
        (p,p_new) = (p_new,p)
        
        iteration += 1      
    #reverse so curr_prob is the current probability
    (curr_prob,prev_prob) = (prev_prob,curr_prob)
    if prob_diff < 0:
        print>>sys.stderr, "Kmeans got worse, diff: {0}".format(prob_diff)
        (curr_prob,prev_prob) = (prev_prob,curr_prob)
        (p,p_new) = (p_new,p)
    print >> sys.stderr, "Kmeans iterations: {0}".format(iteration)
    
    #Get current clustering
    z = log_probabilities(contigs,p)
    #Find each contigs most likely cluster
    clustering = np.argmax(z,axis=1)
    return (clustering, curr_prob, p)
