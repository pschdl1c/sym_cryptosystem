import numpy as np


class TPM:
    """
    Tree Parity Machine class as Hopfield network class for pattern recognition and memory recall
    """
    def __init__(self, k=6, n=4, l=6):
        """
        Initializes Hopfield network with k neurons, n inputs, and weight range of [-l, l]
        """
        self.k = k
        self.n = n
        self.l = l
        self.W = np.random.randint(-l, l + 1, [k, n])

    def get_output(self, X):
        """
        Computes the output of the Hopfield network for a given input
        """
        sigma = np.sign(np.sum(X * self.W, axis=1))
        np.place(sigma, sigma == 0, -1)
        self.tau = np.prod(sigma)
        self.X = X
        self.sigma = sigma
        return self.tau

    def __call__(self, X):
        """
        Allows calling the class as a function to compute the output
        """
        return self.get_output(X)

    def update(self, tau2, update_rule='hebbian'):
        """
        Updates the weights of the network based on the update rule
        """
        if (self.tau == tau2):
            if update_rule == 'hebbian':
                hebbian(self.W, self.X, self.sigma, self.tau, tau2, self.l)
            elif update_rule == 'anti_hebbian':
                anti_hebbian(self.W, self.X, self.sigma, self.tau, tau2, self.l)
            elif update_rule == 'random_walk':
                random_walk(self.W, self.X, self.sigma, self.tau, tau2, self.l)
            else:
                raise ValueError("Invalid update rule.")
        return

def theta(t1, t2):
    """
    Is equal function
    """
    return t1 == t2

def hebbian(W, X, sigma, tau1, tau2, l):
    """
    Hebbian update rule for the weights
    """
    for (i, j), _ in np.ndenumerate(W):
        W[i, j] += X[i, j] * tau1 * theta(sigma[i], tau1) * theta(tau1, tau2)
        W[i, j] = np.clip(W[i, j] , -l, l)
        return W

def anti_hebbian(W, X, sigma, tau1, tau2, l):
    """
    Anti-Hebbian update rule for the weights
    """
    for (i, j), _ in np.ndenumerate(W):
        W[i, j] -= X[i, j] * tau1 * theta(sigma[i], tau1) * theta(tau1, tau2)
        W[i, j] = np.clip(W[i, j], -l, l)

def random_walk(W, X, sigma, tau1, tau2, l):
    """
    Random walk update rule for the weights
    """
    for (i, j), _ in np.ndenumerate(W):
        W[i, j] += X[i, j] * theta(sigma[i], tau1) * theta(tau1, tau2)
        W[i, j] = np.clip(W[i, j] , -l, l)