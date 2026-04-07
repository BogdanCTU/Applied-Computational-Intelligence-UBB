<!-- --------------------------------------------------------------- -->
<!-- --------------------- COURSE 3 CLUSTERING --------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 3 - Clustering**

## 📖 3.1 Definition of Clustering

🔴 **Clustering is the task of dividing data points into groups**, which are called **clusters**:
* **Data points in the same cluster are highly similar to each other**;
* **Data points in different clusters are highly different from each other**;
* **It is an unsupervised learning method**. This means the algorithm finds patterns on its own without using pre-labeled data;
* The input is usually a vector, which is just a list of numbers representing a single data point.

---

## 📖 3.2 Types of Clustering
* **Hard Clustering**: A data point completely belongs to one specific cluster, or it does not.
Example: A store places a customer exactly into group A;
* **Soft Clustering**: A data point is given a probability or chance, of belonging to different clusters.
Example: A customer has a 70% chance of being in group A and a 30% chance of being in group B.

---

## 📖 3.3 Distance Metrics
🔴 **Distance metrics are math formulas used to measure how similar two objects are**.
We treat the objects as vectors, $g_{1}$ and $g_{2}$.
* **Euclidean distance**: The straight-line distance between two points.
Formula: $d(g_{1},g_{2})=\sqrt{\sum_{i=1}^{n}(x_{i}-y_{i})^{2}}$.
* **Manhattan distance**: The distance measured along axes at right angles, like walking city blocks.
Formula: $d(g_{1},g_{2})=\sum_{i=1}^{n}|(x_{i}-y_{i})|$.
* **Minkowski distance**: A flexible formula that generalizes the two above.
Formula: $d(g_{1},g_{2})=\sqrt[m]{\sum_{i=1}^{n}(x_{i}-y_{i})^{m}}$.

---

## 📖 3.4 Clustering Models

### 📑 3.4.1 Hierarchical Clustering (Connectivity Model)

🔴 **Connectivity models group points based on the idea that closer points in space are more similar**.

* **Bottom-Up Approach**: Starts by treating every single data point as its own separate cluster. It repeatedly merges the closest pair of clusters together. It stops when all points are combined into one single giant cluster;
* **Dendrogram**: A tree-like diagram that shows the history of how clusters were merged.  The root is the final giant cluster, and the leaves are the starting single points.

Similarity Measures:
* **Single-link**: Measures distance by looking only at the two closest (most similar) points between two clusters;
* **Complete-link**: Measures distance by looking at the two farthest (most dissimilar) points between two clusters.

### 📑 3.4.2 K-Means Clustering (Centroid Model)

🔴 **Centroid models group points based on how close they are to a central point**, **known as the centroid**.

Algorithm Steps:
1) Choose K, which is the exact number of clusters you want to find;
2) Randomly assign points to K clusters and calculate the center (centroid) for each group;
3) Measure the distance from each point to every center. Move the point to the cluster with the closest center;
4) Recalculate the centers based on the new groups;
5) Repeat steps 3 and 4 until the centers stop moving.

| Feature           | Hierarchical Clustering                                   | K-Means Clustering                          |
|-------------------|-----------------------------------------------------------|---------------------------------------------|
| Speed             | Slow, time complexity is O(n³).                           | Fast, time complexity is O(n).              |
| Number of Clusters| Decided at the end by cutting the dendrogram tree.        | Must be known and set before starting.      |
| Consistency       | Always produces the exact same results.                   | Results can change because starting points are random. |
| Best Used For     | Discovering hidden tree-like structures.                  | Data where clusters are round (spherical).  |

---

## 📖 3.5 Evaluation Metrics
Metrics are used to score how good the resulting clusters are.

### 📑 3.5.1 Internal Metrics
Used when you do not know the true groups. They check for compactness (points are packed tightly) and separation (clusters are far apart);
* **Silhouette Coefficient**: Measures if a point is close to its own cluster but far from others. Scores range from -1 to 1, and closer to 1 is better;
* **Dunn Index**: The ratio of the shortest distance between clusters to the largest cluster size. Higher scores mean tighter, better-separated clusters;
* **Inertia**: The sum of squared distances between points and their centers. Lower scores mean tighter clusters;
* **Davies-Bouldin Index** (_DBI_): Calculates the ratio of distances inside a cluster compared to distances between clusters. A lower score is better;
* **Calinski-Harabasz Index**: Measures how spread apart the clusters are compared to how spread apart the points inside a cluster are. A higher score is better.

### 📑 3.5.2 External Metrics
Used when you already know the true, correct groups (ground truth labels) to compare against.
* **Adjusted Rand Index** (_ARI_): Looks at pairs of points to see if the algorithm grouped them correctly. It adjusts for random guessing. A score of 1.0 is perfect, while 0.0 is random;
* **Rand Index** (_RI_): Measures the percentage of correctly grouped pairs, but does not adjust for random guessing;
* **Jaccard Index**: Measures shared correct pairs divided by the total number of unique pairs;
* **Normalized Mutual Information** (_NMI_): Measures how much correct information is shared between the true groups and the predicted groups. Scores range from 0 to 1.
