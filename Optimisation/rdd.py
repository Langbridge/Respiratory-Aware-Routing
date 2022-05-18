import math

def vent_rate(sex, hr):
    # see O_01 for citation
    if sex=='M':
        return math.exp(0.021*hr + 1.03)
    else:
        return math.exp(0.023*hr + 0.57)

def inhaled_frac(mmd):
    return 1 - 0.5*(1 - 1/(1 + 0.00076 * mmd**2.8))

def deposition_frac(mmd):
    return inhaled_frac(mmd) * (0.0587 + 0.911/(1 + math.exp(4.77 + 1.485 * math.log(mmd))) + 0.943/(1 + math.exp(0.508 - 2.58 * math.log(mmd))))

def calc_rdd(sex, hr, duration, exposure, mmd=0.53):
    # print(f"\tMinute Ventilation: {vent_rate(sex, hr):.2f} L/min")
    return vent_rate(sex, hr) * deposition_frac(mmd) * duration * exposure / 1000

mmd = 0.53 # average mass median diameter of recieved PM while cycling (see SIOT report for citation)

# sex = 'M' # sex of cyclist

# hr = 94 # estimated HR cycling on the leg with zero assistance
# duration = 3 # estimated duration of the leg based on the speed & distance
# exposure = 1 # estimated exposure level on the leg

# print(f"Recieved dose cycling at {hr}bpm for {duration}minutes:\t{calc_rdd(sex, hr, mmd, duration, exposure):.2f}ug")
# print(f"Recieved dose in the car (66bpm) for {duration}minutes:\t{calc_rdd(sex, 66, 0.61, duration, exposure):.2f}ug")