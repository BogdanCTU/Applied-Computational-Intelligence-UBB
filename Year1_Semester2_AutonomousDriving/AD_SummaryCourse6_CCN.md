<!-- --------------------------------------------------------------- -->
<!-- -------------------- COURSE 6 INTRODUCTION -------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 6 - CNN  to Autonomous Driving**

---

## 📖 1.1 Introduction to Autonomous Driving

Quick Math Refresher & Optimization

Derivative: A value that describes how sensitive a mathematical function is to a microscopic change in its input. It represents the tangent of the slope of the function.

Partial Derivative: Similar to a regular derivative, but used for functions with multiple inputs. It measures the sensitivity of the function along just one specific input dimension.

Gradient: A mathematical vector that groups together all the partial derivatives of a function. It points in the direction where the function increases the fastest (steepest ascent).

Objective Function: A formula, such as negative log-likelihood, that a machine learning model tries to minimize.

Gradient Descent Algorithm: A method that starts with a random guess and takes steps in the direction of the negative slope to find the local minimum of an objective function.

Backpropagation Algorithm: A process used to compute the gradient. It first calculates the prediction (forward propagation) and then computes the partial derivatives backward using the recursive chain rule.

Minibatch: A small, random subset of training data. Stochastic Gradient Descent (SGD) uses minibatches to estimate the gradient because calculating the exact error over the entire dataset is too computationally expensive. Larger minibatches increase gradient accuracy and parallelism, but they consume more memory and decrease the regularization effect.

Regularization: Techniques used to prevent a model from simply memorizing data. Examples include early stopping, data augmentation (mirroring, rotating, or scaling images), weight decay, and dropout.

Precursors: Multi-Layer Perceptrons (MLPs)

Multi-Layer Perceptron (MLP): An early network design composed of Fully Connected (FC) layers.



Shutterstock

Esplora

Fully Connected (FC) Layer: A layer where every input element connects to every output element. It processes data in two stages:

Linear Projection Stage: Multiplies the input feature vector by learned parameters (weights) to create a new linear combination.

Detector Stage: Applies a non-linear mathematical function to decide if a matched pattern is strong enough. A common detector is the Rectified Linear Unit (ReLU), defined as $y=max(0,x)$. Other functions include the logistic and softplus functions.

Limitations of MLPs: They do not exploit the spatial structure of images and require a massive number of parameters. For example, a 256 by 256 image requires 1 million parameters in a single FC layer, which easily leads to overfitting.

Convolutional Layers

Convolutional Neural Networks (CNNs): Networks designed to scan for small, local patterns and successively group them into larger, more abstract patterns.

Convolution Stage: Replaces fully connected topology by exploiting the grid-like structure of images. It uses a Kernel (or filter), which is a small matrix of weights, and slides it over the input data. At each position, it calculates the sum of element-wise multiplications.

This approach massively reduces the number of parameters compared to FC layers and makes the network equivariant to spatial translation (shifting).

Meta-Parameters of Convolution:

Stride: Controls the step size when sliding the kernel along the horizontal or vertical axes. A larger stride reduces the output size and computational complexity.

Padding: The addition of zeros around the borders of the input matrix. This prevents the outer edges of the data from being lost and keeps the input-to-output size ratio consistent.

The Pooling Stage

Pooling Layer: A layer that slides a window over the data and extracts a single summary statistic from the neighboring features.

The primary goals of pooling are to add invariance to small translations (shifts) in the input and to downsample the signal.

Max Pooling: The most common pooling statistic, which acts as a "winner takes all" mechanism by only keeping the highest value in the window. Average pooling is an alternative that smooths out detection noise.

Output Layers

Output Layer: A final transformation layer required because raw network outputs cannot always represent valid probability functions. It restricts the output to a parametric family of Probability Mass Functions (PMF) or Probability Density Functions (PDF).

Sigmoid Output Layer: Used for binary classification (two outcomes). It outputs a single scalar probability constrained between 0 and 1.

Softmax Output Layer: Used for generic classification (multiple outcomes). It forces a vector of raw scores into a list of probabilities where all values fall between 0 and 1, and their total sum exactly equals 1.

Regression: For continuous number prediction, the network can output parameters like the mean without needing a specialized PMF output layer. This minimizes the Euclidean distance between predictions and ground truth, known as Ordinary Least Squares.

Batch Normalization

Batch Normalization Layer: A layer introduced to solve the problem of uneven activation scales, which causes different sensitivities for different parameters during training.

It computes the mean and variance for each feature over the current minibatch. It then normalizes the data by subtracting the mean and dividing by the variance, keeping the data uniformly scaled.