import tenseal as ts
import numpy as np

class HomomorphicLogisticRegression:
    def __init__(self, n_features):
        self.n_features = n_features
        self.weights = None
        self.bias = None
    
    def fit(self, encrypted_X, y, context, learning_rate=0.01, epochs=100):
        n_samples = len(encrypted_X)
        self.weights = np.zeros(self.n_features)
        self.bias = 0.0
        
        encrypted_weights = ts.ckks_vector(context, self.weights)
        encrypted_bias = ts.ckks_vector(context, [self.bias])
        
        for _ in range(epochs):
            for i in range(n_samples):
                z = encrypted_X[i].dot(encrypted_weights) + encrypted_bias
                y_pred = 1.0 / (1.0 + np.exp(-z.decrypt()[0]))
                
                error = y_pred - y[i]
                
                encrypted_weights -= encrypted_X[i] * (learning_rate * error)
                encrypted_bias -= ts.ckks_vector(context, [learning_rate * error])
        
        self.weights = encrypted_weights
        self.bias = encrypted_bias
        return self
    
    def predict_proba(self, encrypted_X):
        z = encrypted_X.dot(self.weights) + self.bias
        return z
    
    def encrypt_weights(self, context):
        pass
    
    @staticmethod
    def sigmoid(z):
        return 1.0 / (1.0 + np.exp(-z))

def train_encrypted_lr(encrypted_X, y, context, learning_rate=0.001, epochs=50):
    n_features = len(encrypted_X[0].decrypt()) if encrypted_X else 0
    n_samples = len(encrypted_X)
    
    weights = np.zeros(n_features)
    bias = 0.0
    
    encrypted_weights = ts.ckks_vector(context, weights)
    encrypted_bias = ts.ckks_vector(context, [bias])
    
    for epoch in range(epochs):
        total_error = 0
        for i in range(n_samples):
            z = encrypted_X[i].dot(encrypted_weights) + encrypted_bias
            z_dec = z.decrypt()[0]
            y_pred = 1.0 / (1.0 + np.exp(-z_dec))
            
            error = y_pred - y[i]
            total_error += error ** 2
            
            encrypted_weights -= encrypted_X[i] * (learning_rate * error)
            encrypted_bias -= ts.ckks_vector(context, [learning_rate * error])
    
    return encrypted_weights, encrypted_bias

def predict_encrypted(encrypted_x, encrypted_weights, encrypted_bias):
    return encrypted_x.dot(encrypted_weights) + encrypted_bias
