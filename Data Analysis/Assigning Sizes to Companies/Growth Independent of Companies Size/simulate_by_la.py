import csv
from scipy.stats import lognorm
import datetime
import numpy as np

import matplotlib.pyplot as plt


def main():
    ages_by_la = get_ages_by_la()
    la_params  = get_la_params()
    total_employment = get_total_employment()


    #predict employment
    results = {'x': [], 'y': []}
    for la, ages in ages_by_la.items():
        if la not in la_params or la not in total_employment:
            continue
        total = 0
        mean = la_params[la]['mean']
        sd = la_params[la]['sd']

        #mean = 0.0001
        #sd = 0.00001

        for age, n in ages.items():
            if age == 0:
                continue
            try:
                total += np.sum(lognorm.rvs(sd * age, loc=np.exp(mean * age), size=n))
            except:
                print(mean * age, mean, age)
        if total_employment[la] < 3 * total and total < 3 * total_employment[la]:
            results['x'].append(total_employment[la])
            results['y'].append(total)

    plt.scatter(results['x'], results['y'])
    plt.show()

def get_total_employment():
    las = {}
    with open('../2012_Employment_Totals.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for line in reader:
            las[line[0]] = int(float(line[1]) * 1000)
    return las

def get_la_params():
    las = {}
    with open('../parameters_by_local_authority.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for line in reader:
            las[line[0]] = {'mean': float(line[1]), 'sd': float(line[2])}
    return las

def get_ages_by_la():
    las = {}
    files = ['../2012-Snapshot.csv']
    for f in files:
        with open(f, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for line in reader:
                if line[1] in las:
                    if int(line[2]) in las[line[1]]:
                        las[line[1]][int(line[2])] += 1
                    else:
                        las[line[1]][int(line[2])] = 1
                else:
                    las[line[1]] = { int(line[2]): 1}

    return las


if __name__ == '__main__':
    main()
