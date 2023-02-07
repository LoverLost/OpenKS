"""
===================================================================================
Performing cross-validation n times, optimizing SVM's and kernel's hyperparameters.
===================================================================================

Script makes use of :class:`grakel.WeisfeilerLehman`, :class:`grakel.VertexHistogram`
"""
from __future__ import print_function
print(__doc__)

import numpy as np

from grakel.datasets import fetch_dataset
from grakel.utils import cross_validate_Kfold_SVM
from grakel.kernels import WeisfeilerLehman, VertexHistogram

# Loads the MUTAG dataset
MUTAG = fetch_dataset("MUTAG", verbose=False)
G, y = MUTAG.data, MUTAG.target

# Generates a list of kernel matrices using the Weisfeiler-Lehman subtree kernel
# Each kernel matrix is generated by setting the number of iterations of the
# kernel to a different value (from 2 to 7)
Ks = list()
for i in range(1, 7):
	gk = WeisfeilerLehman(n_iter=i, base_graph_kernel=VertexHistogram, normalize=True)
	K = gk.fit_transform(G)
	Ks.append(K)


# Performs 10-fold cross-validation over different kernels and the parameter C of 
# SVM and repeats the experiment 10 times with different folds
accs = cross_validate_Kfold_SVM([Ks], y, n_iter=10)
print("Average accuracy:", str(round(np.mean(accs[0])*100, 2)) + "%")
print("Standard deviation:", str(round(np.std(accs[0])*100, 2)) + "%")