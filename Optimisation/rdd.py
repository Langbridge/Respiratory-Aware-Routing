import math

def vent_rate(sex, hr):
    '''
    Returns the subject's ventilation rate.

            Parameters:
                    sex (str): 'M' or 'F', the sex of the individual
                    HR (float): The heart rate for the period of interest, bpm

            Returns:
                    VR (float): Ventilation rate of the individual, L/min
    '''
    
    if sex=='M':
        return math.exp(0.021*hr + 1.03)
    else:
        return math.exp(0.023*hr + 0.57)

def inhaled_frac(mmd):
    '''
    Returns the fraction of particles that are inhaled.

            Parameters:
                    mmd (str): The mass-median diameter of inhaled particles, um

            Returns:
                    IF (float): Fraction of particles that are inhaled
    '''
    return 1 - 0.5*(1 - 1/(1 + 0.00076 * mmd**2.8))

def deposition_frac(mmd):
    '''
    Returns the fraction of particles that are deposited in the lungs.

            Parameters:
                    mmd (str): The mass-median diameter of inhaled particles, um

            Returns:
                    DF (float): Fraction of particles that are deposited
    '''
    return inhaled_frac(mmd) * (0.0587 + 0.911/(1 + math.exp(4.77 + 1.485 * math.log(mmd))) + 0.943/(1 + math.exp(0.508 - 2.58 * math.log(mmd))))

def calc_rdd(sex, hr, duration, exposure, mmd=0.53):
    '''
    Returns the RDD for a discrete period of interest for a given subject at HR.

            Parameters:
                    sex (str): 'M' or 'F', the sex of the individual
                    HR (float): The heart rate for the period of interest, bpm
                    duration (float): The length of the period of interest, minutes
                    exposure (float): The concentration of PM2.5 over the period of interest, ug/m3

            Returns:
                    RDD (float): Recieved deposition dose over the period of interest, ug
    '''
    return vent_rate(sex, hr) * deposition_frac(mmd) * duration * exposure / 1000

mmd = 0.53 # average mass median diameter of recieved PM while cycling (see report for citation)