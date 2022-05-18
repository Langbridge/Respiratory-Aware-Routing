import numpy as np

# MODEL PARAMS
d_ae = 1 # aerodynamic particle diameter, um
U = 1
SF_i = 1
SF_a = 1
SF_b = 1
V_D = {'ET': 50, 'BB': 49, 'bb': 47}

class Mouth():
    NUM_FILTERS = 4

    a_th = {1: 9, 2: np.NaN, 3: -76.8 + 167*pow(SF_b, np.NaN), 4: 170 + 103*pow(SF_a, 2.13)}
    R_th = {1: np.NaN, 2: Dt_B, 3: Dt_b, 4: Dt_a}
    p_th = {1: 0.5, 2: 0.6391, 3: 0.5676, 4: 0.6101}
    a_ae = {1: 1.1e-4, 2: 4.08e-6, 3: 0.1147, 4: 0.1146*pow(SF_a, 0.98)}
    R_ae = {1: }
    p_ae = {1: 1.4, 2: 1.152, 3: 1.173, 4: 0.6495}

    # FUNCTIONS
    def n_ae(self, j):
        if j <= self.NUM_FILTERS:
            return 1 - np.exp(- self.a_ae[j] * pow(self.R_ae[j], self.p_ae[j]))
        else:
            idx = self.NUM_FILTERS - (j - self.NUM_FILTERS)
            return 1 - np.exp(- self.a_ae[idx] * pow(self.R_ae[idx], self.p_ae[idx]))

    def n_th(self, j):
        if j <= self.NUM_FILTERS:
            return 1 - np.exp(- self.a_th[j] * pow(self.R_th[j], self.p_th[j]))
        else:
            idx = self.NUM_FILTERS - (j - self.NUM_FILTERS)
            return 1 - np.exp(- self.a_th[idx] * pow(self.R_th[idx], self.p_th[idx]))

    def efficiency(self, j):
        if j == 1:
            return 1 - 0.5*(1 - pow(7.6e-4 * pow(d_ae, 2.8) + 1, -1) + 1e-5 * pow(U, 2.75) * np.exp(0.055 * d_ae))
        else:
            return pow(self.n_ae(j)**2 + self.n_th(j)**2, 0.5)

    def deposition_frac(self, j):
        if j == 1:
            return self.efficiency(1) * (1 - self.efficiency(0))
    