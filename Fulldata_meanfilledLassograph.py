# -*- coding: utf-8 -*-
"""
Created on Sun Mar 11 10:12:10 2018

@author: Haoyuan
"""

import numpy as np
import DBhelper as DBh
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from sklearn import cluster, covariance, manifold
import json

def read_daily_data(con):
    """ Read from MySQL database the required quotes of hs300 stocks
        args:
            con: a sqlalchemy engine connection
            stock: a list of stocks' code to fetch
            start: beginning date of historical price
            end: ending date 
        return:
            daily variation of stock price;
            valid stock code (for the purpose of same sample size)
    """
    newopen=pd.read_sql('select * from cnstock.open',con)
    newclose=pd.read_sql('select * from cnstock.close',con)
    print newopen.tail()
    newopen.fillna(newopen.mean(), inplace=True)
    newclose.fillna(newclose.mean(), inplace=True)
#    newopen.interpolate()
#    newclose.interpolate()
#    print newopen.isnull().sum()
#    print newclose.isna().sum()
#    newopen.fillna(method='ffill', inplace=True)
#    newopen.fillna(method='bfill', inplace=True)
#    newclose.fillna(method='ffill', inplace=True)
#    newclose.fillna(method='bfill', inplace=True)


    open_prices=newopen.values.T[1:]
    close_prices=newclose.values.T[1:]
    variation=np.float64(close_prices-open_prices)
    return variation

engine=DBh.connect('root','87566766','127.0.0.1:3306','cnstock')

#print json.dumps(symbols, encoding="UTF-8", ensure_ascii=False)
########################################################
symbols=pd.read_sql('SELECT code, name from cnstock.hs300',engine)
code=symbols['code']
#symbolsdict=dict(zip(symbols['code'],symbols['name']))
variation=read_daily_data(engine)

codes, names=symbols.as_matrix().T


 #############################################################################
# Learn a graphical structure from the correlations
edge_model = covariance.GraphLassoCV()

# standardize the time series: using correlations rather than covariance
# is more efficient for structure recovery

X = variation.copy().T
print X
X /= X.std(axis=0)
edge_model.fit(X)

## #############################################################################
# Cluster using affinity propagation

_, labels = cluster.affinity_propagation(edge_model.covariance_)
n_labels = labels.max()

for i in range(n_labels + 1):
    print'Cluster %i: %s' % ((i + 1), ', '.join(names[labels == i]))
    
    
 #############################################################################
# Find a low-dimension embedding for visualization: find the best position of
# the nodes (the stocks) on a 2D plane
#
# We use a dense eigen_solver to achieve reproducibility (arpack is
# initiated with random vectors that we don't control). In addition, we
# use a large number of neighbors to capture the large-scale structure.
node_position_model = manifold.LocallyLinearEmbedding(
    n_components=2, eigen_solver='dense', n_neighbors=6)

embedding = node_position_model.fit_transform(X.T).T
# ###########################################################################
# Visualization
plt.figure(1, facecolor='w', figsize=(30, 30))
plt.clf()
ax = plt.axes([0., 0., 1., 1.])
plt.axis('off')

# Display a graph of the partial correlations
partial_correlations = edge_model.precision_.copy()
d = 1 / np.sqrt(np.diag(partial_correlations))
partial_correlations *= d
partial_correlations *= d[:, np.newaxis]
non_zero = (np.abs(np.triu(partial_correlations, k=1)) > 0.02)

# Plot the nodes using the coordinates of our embedding
plt.scatter(embedding[0], embedding[1], s=100 * d ** 2, c=labels,
            cmap=plt.cm.spectral)

# Plot the edges
start_idx, end_idx = np.where(non_zero)
# a sequence of (*line0*, *line1*, *line2*), where::
#            linen = (x0, y0), (x1, y1), ... (xm, ym)
segments = [[embedding[:, start], embedding[:, stop]]
            for start, stop in zip(start_idx, end_idx)]
values = np.abs(partial_correlations[non_zero])
lc = LineCollection(segments,
                    zorder=0, cmap=plt.cm.hot_r,
                    norm=plt.Normalize(0, .7 * values.max()))
lc.set_array(values)
lc.set_linewidths(15 * values)
ax.add_collection(lc)

# Add a label to each node. The challenge here is that we want to
# position the labels to avoid overlap with other labels
for index, (name, label, (x, y)) in enumerate(
        zip(names, labels, embedding.T)):

    dx = x - embedding[0]
    dx[index] = 1
    dy = y - embedding[1]
    dy[index] = 1
    this_dx = dx[np.argmin(np.abs(dy))]
    this_dy = dy[np.argmin(np.abs(dx))]
    if this_dx > 0:
        horizontalalignment = 'left'
        x = x + .002
    else:
        horizontalalignment = 'right'
        x = x - .002
    if this_dy > 0:
        verticalalignment = 'bottom'
        y = y + .002
    else:
        verticalalignment = 'top'
        y = y - .002
    plt.text(x, y, name, size=16,
             horizontalalignment=horizontalalignment,
             verticalalignment=verticalalignment,
             bbox=dict(facecolor='w',
                       edgecolor=plt.cm.spectral(label / float(n_labels)),
                       alpha=.6))

plt.xlim(embedding[0].min() - .15 * embedding[0].ptp(),
         embedding[0].max() + .10 * embedding[0].ptp(),)
plt.ylim(embedding[1].min() - .03 * embedding[1].ptp(),
         embedding[1].max() + .03 * embedding[1].ptp())

plt.show()    
##%%
#engine=connect('root','87566766','localhost','cnstock')
#code=ts.get_hs300s()[['code']]
#stock=list(code.values.reshape(1,-1)[0])
#for s in stock:
#    try:
#        engine.execute('DROP TABLE cnstock.%s' %(s))
#    except:
#        continue
