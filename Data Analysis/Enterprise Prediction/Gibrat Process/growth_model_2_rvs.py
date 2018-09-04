import csv, datetime
import numpy as np
from scipy.stats import lognorm
from scipy.optimize import fsolve, root


def main():

    print('Getting local authority and SIC code expectations')
    la_target_means, la_target_variances = get_targets_by_la()
    sic_target_means, sic_target_variances = get_targets_by_sic()

    local_authorities = []
    sic_codes = []

    target_means = []
    target_variances = []

    for la, mean in la_target_means.items():
        local_authorities.append(la)
        target_means.append(mean)
        target_variances.append(la_target_variances[la])

    for sic, mean in sic_target_means.items():
        sic_codes.append(sic)
        target_means.append(mean)
        target_variances.append(sic_target_variances[sic])

    print('done')

    print('Getting companies...')
    companies = get_companies(la_target_means, sic_target_means)
    print('done')

    print('Sorting Companies...')
    bins = {la: {sic: {} for sic in sic_codes} for la in local_authorities}
    for company in companies:
        if company['age'] in bins[company['la']][company['sic']]:
            bins[company['la']][company['sic']][company['age']] += 1
        else:
            bins[company['la']][company['sic']][company['age']] = 1

    print('done')

    #print((np.array(target_means) ** 2).mean())

    #print(fsolve(expectation, np.zeros(len(local_authorities) + len(sic_codes)) * 0.00000001, args=(target_means, bins, local_authorities, sic_codes)))
    means = np.ones(len(local_authorities) + len(sic_codes)) * 0.003

    means = root(expectation, np.ones(len(local_authorities) + len(sic_codes)) * 0.003, args=(np.array(target_means), bins, local_authorities, sic_codes), method='lm', jac=expectation_jacobian).x
    variances = root(variance, np.ones(len(local_authorities) + len(sic_codes)) * 0.001, args=(np.array(target_variances), means, bins, local_authorities, sic_codes), method='lm', jac=variance_jacobian).x

    #print(mean, variances)

    with open('parameters.csv', 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(local_authorities + sic_codes)
        writer.writerow(means)
        #writer.writerow(variances)



def expectation(params, target, age_bins, local_authorities, sic_codes):
    expectations = np.zeros(len(local_authorities) + len(sic_codes))
    bins  = np.zeros(len(local_authorities) + len(sic_codes))

    total_las = len(local_authorities)

    for la, sic_bin in age_bins.items():
        la_index = local_authorities.index(la)
        for sic, ages in sic_bin.items():
            sic_index = sic_codes.index(sic)

            la_param = params[la_index]
            sic_param = params[total_las + sic_index]

            total = 0

            for age, n in ages.items():
                expectations[la_index] += n * (1 + la_param + sic_param) ** age
                expectations[total_las + sic_index] += n * (1 + la_param + sic_param) ** age

                total += n

            bins[la_index] += total
            bins[total_las + sic_index] += total

    #print(np.mean(target))
    print(np.mean((expectations / bins - target) ** 2))

    return expectations / bins - target


def variance(params, target, means, age_bins, local_authorities, sic_codes):
    variances = np.zeros(len(local_authorities) + len(sic_codes))
    totals = np.zeros(len(local_authorities) + len(sic_codes))
    covariances = np.zeros(len(local_authorities) + len(sic_codes))
    total_las = len(local_authorities)
    age_vector = [[] for _ in range(len(local_authorities) + len(sic_codes))]






    for la, sic_bin in age_bins.items():
        la_index = local_authorities.index(la)
        for sic, ages in sic_bin.items():
            sic_index = sic_codes.index(sic)
            for age, n in ages.items():
                totals[la_index] += n
                totals[total_las + sic_index] += n

                variances[la_index] += n * (params[la_index] ** 2 + params[total_las + sic_index] ** 2) ** age
                age_vector[la_index].append(n * (1 + means[la_index] + means[total_las + sic_index]) ** age)

    for i, arr in enumerate(age_vector):
        covariances -= np.outer(arr, arr).sum()

    variances = variances / totals + covariances / totals ** 2



    print(np.mean((variances - target) ** 2))

    return variances - target




def expectation_jacobian(params, target, age_bins, local_authorities, sic_codes):
    size = len(local_authorities) + len(sic_codes)
    number_of_local_authorities = len(local_authorities)
    jacobian = np.zeros((size, size))

    totals = np.zeros((size, size))
    total_las = len(local_authorities)


    for la, sic_bin in age_bins.items():
        la_index = local_authorities.index(la)
        for sic, ages in sic_bin.items():
            sc_index = sic_codes.index(sic)


            for age, n in ages.items():
                size_deriv = age * n * (1 + params[la_index] + params[number_of_local_authorities + sc_index]) ** (age - 1)
                jacobian[la_index][la_index] += size_deriv
                jacobian[number_of_local_authorities + sc_index][number_of_local_authorities + sc_index] += size_deriv

                jacobian[la_index][number_of_local_authorities + sc_index] += size_deriv
                jacobian[number_of_local_authorities + sc_index][la_index] += size_deriv

                totals[la_index] += n
                totals[number_of_local_authorities + sc_index] += n

    #print(jacobian)

    return np.divide(jacobian, totals)

def variance_jacobian(params, target, means, age_bins, local_authorities, sic_codes):
    size = len(local_authorities) + len(sic_codes)
    jacobian = np.zeros((size, size))

    totals_by_la = {la: 0 for la in local_authorities}
    totals_by_sic = {sic: 0 for sic in sic_codes}


    total_las = len(local_authorities)


    for la, sic_bin in age_bins.items():
        for sic, ages in sic_bin.items():
            for n in ages.values():
                totals_by_la[la] += n
                totals_by_sic[sic] += n




    for la, sic_bin in age_bins.items():
        la_index = local_authorities.index(la)
        for sic, ages in sic_bin.items():
            sic_index = sic_codes.index(sic)

            la_param = params[la_index]
            sic_param = params[total_las + sic_index]

            for age, n in ages.items():
                d_var = ((la_param ** 2 + sic_param ** 2) + (1 + means[la_index] + means[total_las + sic_index]) ** 2) ** (age - 1)
                jacobian[la_index][la_index] += (n / totals_by_la[la]) * 2 * la_param * d_var
                jacobian[total_las + sic_index][total_las + sic_index] += (n / totals_by_sic[sic]) * 2 * sic_param * d_var

                jacobian[la_index][total_las + sic_index] += (n / totals_by_la[la]) * 2 * la_param * d_var
                jacobian[total_las + sic_index][la_index] += (n / totals_by_sic[sic]) * 2 * sic_param * d_var


    return jacobian


def get_companies(las, sics):
    date = datetime.datetime(2017, 1, 1)
    companies = []
    files = ['../Data/CH/Company_Data/' + str(i) + '.csv' for i in range(7)]
    for file in files:
        with open(file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for line in reader:
                try:
                    sic = int(line[1][:2])
                except:
                    continue
                la = line[5]

                if sic not in sics or la not in las:
                    continue
                if (date - datetime.datetime.strptime(line[3], '%Y-%m-%d')).days > 0:
                    continue
                age = int((date - datetime.datetime.strptime(line[2], '%Y-%m-%d')).days / 28)
                #age = 1
                companies.append({'sic': sic, 'la': la, 'age': age})

    return companies

def get_targets_by_sic():
    means = {}
    variances = {}
    with open('../Data/2017_2_sic_enterprise_lognormal_params.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for line in reader:
            sic = int(line[0])
            mu = float(line[1])
            sigma = float(line[2])

            if mu == 0 and sigma == 1:
                continue
            if sigma > 10:
                continue

            mean, variance = get_mean_varaince_of_lognorm(mu, sigma)
            if mean < 500:
                means[sic] = mean
                variances[sic] = variance
    return means, variances

def get_targets_by_la():
    means = {}
    variances = {}

    with open('../Data/2017_la_enterprise_lognormal_params.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for line in reader:
            la = line[0]
            mu = float(line[1])
            sigma = float(line[2])

            mean, variance = get_mean_varaince_of_lognorm(mu, sigma)

            means[la] = mean
            variances[la] = variance

    return means, variances


def get_mean_varaince_of_lognorm(mu, sigma):
    return lognorm.mean(sigma, scale=np.exp(mu)), lognorm.var(sigma, scale=np.exp(mu))

if __name__ == '__main__':
    main()