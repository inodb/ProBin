#!/usr/bin/env python
"""Cluster DNA based on EM algorithm with fixed number of clusters"""
import numpy as np
import sys
from multiprocessing import Pool, cpu_count
from probin.binning import kmeans
from itertools import izip

def cluster(contigs, log_probability_func,fit_nonzero_parameters_func,cluster_count,centroids=None,max_iter=100, repeat=10,epsilon=1E-7):
    (max_clusters, max_clustering_prob,max_centroids) = (None, -np.inf, None)
    params = [(contigs, log_probability_func,fit_nonzero_parameters_func, cluster_count ,np.copy(centroids), max_iter,epsilon) for _ in xrange(repeat)]
    #pool = Pool(processes=cpu_count())
    #results = pool.map(_clustering_wrapper, params)
    #pool.close()
    results = [_clustering_wrapper(param) for param in params]
        
    return max(results,key=lambda x: x[1])

def _clustering_wrapper(params):
    return _clustering(*params)

def _clustering(contigs, log_probability_func,fit_nonzero_parameters_func, cluster_count ,p , max_iter, epsilon):
    if not np.any(p):    
        clustering,_, p = kmeans._clustering(contigs, log_probability_func, fit_nonzero_parameters_func, cluster_count ,p, max_iter=3,epsilon=epsilon)
        n = np.array([len(cluster) for cluster in clustering])
        exp_log_qs, max_log_qs = _get_exp_log_qs(contigs,log_probability_func,p)
        z = _expectation(contigs,log_probability_func,n,exp_log_qs)
        prev_prob,_,_ = _evaluate_clustering(contigs, log_probability_func, p, z)

    else:
        print >> sys.stderr, "Not implemented for EM to start with fixed p (centroids)"
        sys.exit(-1)
        
    prob_diff = np.inf
    prev_prob = -np.inf
    iteration = 0
    
    while(max_iter - iteration > 0 and prob_diff > epsilon):
        z = _expectation(contigs,log_probability_func,n,exp_log_qs)
        p = _maximization(contigs,fit_nonzero_parameters_func,z)        
        curr_prob, exp_log_qs, max_log_qs = _evaluate_clustering(contigs,log_probability_func,p,z)        
        n = np.sum(z,axis=0,keepdims=True)
        
        
        prob_diff = curr_prob - prev_prob
        print curr_prob, prev_prob,prob_diff
        (curr_prob,prev_prob) = (prev_prob,curr_prob)
        iteration += 1
    
    #Change back so curr_prob represents the highest probability
    (curr_prob,prev_prob) = (prev_prob,curr_prob)
    print >> sys.stderr, "iterations: {0}".format(iteration)
    if prob_diff < 0:
        print >> sys.stderr, "Previous probability {0} was greater than current probability {1}. Should never happen in EM".format(prev_prob,curr_prob)
    clustering = [set() for _ in xrange(len(p))]
    which_cluster = np.argmax(z,axis=1)
    for (contig,which) in izip(contigs,which_cluster):
        clustering[which].add(contig)
    return (clustering, curr_prob, p)
def _expectation(contigs, log_probability_func, n, exp_log_qs):
    """
    Usage: _expectation(contigs,log_probability_func, p, n, exp_log_qs, max_log_qs)
    Return: The responsibility matrix for currenct p and n
    
    We are calculating the expression <z_{i,k}> = Q(theta_i|p_k)n_k / sum_{l=1}^K(Q(theta_i|p_l)*n_l)
        where theta is the feature vector of contig_i, p_k is the feature vector of centroid_k and n_k is the expected number
        of contigs in cluster k.
        
        the calculation of <z_{i,k}> can be expressed as:
        
        exp(log(Q(theta_i|p_k) - log(Q(theta_i|p_kmax))))*n_k / sum_{l=1}^K(exp(log(Q(theta_i|p_l))-log(Q(theta_i|p_max)))*n_l)
        
        We see that we get the exp_log_qs=exp(log(Q(theta_i|p_k))-log(Q(theta_i|p_max)) for all i and l and k 
        and the max_log_qs = log(Q(theta_i|p_max) for all i for free from 
        _evaluation_clustering from the previous iteration.
    """
    
    exp_log_qs *= n
    return exp_log_qs / np.sum(exp_log_qs,axis=1,keepdims=True)

def _maximization(contigs, fit_nonzero_parameters_func, z):
    """
    Usage: _maximization(contigs, fit_nonzero_parameters_func, p, z)
    Return: The new centroids that maximize the probability for the current z values.
    
    We are calculating the expression p_{k,j} = sum_i(<z_{i,k}>*theta_{i,j}) / sum_j( sum_i(<z_{i,k}>*theta_{i,j}))
    
    """
    return fit_nonzero_parameters_func(contigs,expected_clustering=z.T)
    

def _evaluate_clustering(contigs, log_probability_func, p, z):
    """
    Usage:  _evaluate_clustering(contigs,log_probability_func, p, z)
    Return: (clustering_prob, exp_log_qs, max_log_qs)
    
    calculate log L(theta|z,p) or log L(contigs| expected_clustering_freq,centroids)
    = sum_{i=1}^{N} (log (sum_{k=1}^{K} (<z_{i,k}>*Q(theta_{i}|p_{k}) ) ) )
    which translates into:
    sum_{i=1}^{N}( log( Q(theta_{i}|p_{kmax}) ) + log( sum_{k=1}^{K}( <z_{i,k}>*exp(log( Q(theta_{i}|p_{k}) ) - log(Q(theta_{i}|p_{kmax}) ) ) ) ) )    
    
    N is the number of contigs, K is the number of clusters.
    
    clustering_prob is the evaluation of the current clustering
    log_qs is an NxK matrix of all log (Q(theta_i|p_k)) values.
    max_log_qs is an Nx1 matrix where each row contains the max value over corresponding row in log_qs

    exp_log_qs and max_log_qs are used in the next iteration in _evaluation.     
    """
    exp_log_qs, max_log_qs = _get_exp_log_qs(contigs,log_probability_func,p)

    clustering_prob = np.sum(max_log_qs + np.log(np.sum(z*exp_log_qs)))
    return clustering_prob, exp_log_qs, max_log_qs
    
def _get_exp_log_qs(contigs,log_probability_func,p):
    log_qs = np.zeros((len(contigs),len(p)))
    for i,contig in enumerate(contigs):
        log_qs[i] = np.fromiter((log_probability_func(contig,centroid) for centroid in p),dtype=float)
    max_log_qs = np.max(log_qs,axis=1,keepdims=True)
    exp_log_qs = np.exp(log_qs - max_log_qs)
    return exp_log_qs, max_log_qs