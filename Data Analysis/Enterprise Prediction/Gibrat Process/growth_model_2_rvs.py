import csv, datetime
import numpy as np
from scipy.stats import lognorm
from scipy.optimize import fsolve, root
from multiprocessing import Pool


def main():
    calculate_means = True
    #calculate_covariances = True

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
    bins = sort_companies(companies, local_authorities, sic_codes)

    print('done')
#    print(expectation(np.zeros(len(local_authorities) + len(sic_codes)), np.array(target_means), bins, local_authorities, sic_codes))

    if calculate_means:
        means = root(expectation, np.ones(len(local_authorities) + len(sic_codes)) * 0.00003, args=(np.array(target_means), bins, local_authorities, sic_codes), method='lm', jac=expectation_jacobian).x
        for i, x in enumerate(expectation(means, np.array(target_means), bins, local_authorities, sic_codes)):
            print(x + target_means[i], target_means[i])
    else:
        print('Loading means...')
        means_from_file = load_means()
        means = np.zeros(len(local_authorities) + len(sic_codes))
        for i, la in enumerate(local_authorities):
            means[i] = float(means_from_file[la])
        for i, sic in enumerate(sic_codes):
            means[len(local_authorities) + i] = float(means_from_file[str(sic)])
        print('done')


    print('Calculating covariance constants...')
    covariances = calculate_covariances(bins, local_authorities, sic_codes, means)
    print('done')
#    else:
#        print('Loading covariance constants..')
#        cvs_from_file = load_means()
#        covariances = np.zeros(len(local_authorities) + len(sic_codes))
#        for i, la in enumerate(local_authorities):
#            covariances[i] = float(cvs_from_file[la])
#        for i, sic in enumerate(sic_codes):
#            covariances[len(local_authorities) + i] = float(cvs_from_file[str(sic)])
#        print('done')

    #print([x for x in variance(np.zeros(len(local_authorities) + len(sic_codes)), np.array(target_variances), means, covariances, bins, local_authorities, sic_codes) if x > 0])

    variances = root(variance, np.ones(len(local_authorities) + len(sic_codes)) * 0.045, args=(np.array(target_variances), means, covariances, bins, local_authorities, sic_codes), method='lm', jac=variance_jacobian).x

    print(means, variances)


def sort_companies(companies, local_authorities, sic_codes):
    
    bins = {la: {sic: {} for sic in sic_codes} for la in local_authorities}
    for company in companies:
        if company['age'] in bins[company['la']][company['sic']]:
            bins[company['la']][company['sic']][company['age']] += 1
        else:
            bins[company['la']][company['sic']][company['age']] = 1
    return bins

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


def variance(params, target, means, covariances, age_bins, local_authorities, sic_codes):
    variances = np.zeros(len(local_authorities) + len(sic_codes))
    totals = np.zeros(len(local_authorities) + len(sic_codes))
    covariances = np.zeros(len(local_authorities) + len(sic_codes))
    total_las = len(local_authorities)

    for la, sic_bin in age_bins.items():
        la_index = local_authorities.index(la)
        for sic, ages in sic_bin.items():
            sic_index = sic_codes.index(sic)
            for age, n in ages.items():
                totals[la_index] += n
                totals[total_las + sic_index] += n

                variances[la_index]
                var = n * (params[la_index] ** 2 + params[total_las + sic_index] ** 2 + (1 + means[la_index] + means[total_las])**2) ** age
                variances[la_index] += var
                variances[total_las + sic_index] += var


    variances = variances / totals - covariances


    print(np.mean((variances - target) ** 2))

    return variances - target

def calculate_covariances(age_bins, local_authorities, sic_codes, means):
    covariances = np.zeros(len(local_authorities) + len(sic_codes))
    totals = np.zeros(len(local_authorities) + len(sic_codes))

    max_age = 0
    for la, sic_bin in age_bins.items():
        la_index = local_authorities.index(la)
        for sic, ages in sic_bin.items():
            sic_index = sic_codes.index(sic)
            for age, n in ages.items():
                if age > max_age:
                    max_age = age
                totals[la_index] += n
                totals[len(local_authorities) + sic_index] += n


    with Pool() as p:
        input = [(i, la, max_age, local_authorities, sic_codes, age_bins, means) for i, la in enumerate(local_authorities)]
        covariances = p.starmap(la_covariance, input)
        input = [(i, sic, max_age, local_authorities, sic_codes, age_bins, means) for i, sic in enumerate(sic_codes)]
        covariances += p.starmap(sic_covariance, input)
    #covariances = [la_covariance(la, max_age, sic_codes, age_bins, means) for la in local_authorities]
    #covariances += [sic_covariance(sic, max_age, local_authorities, age_bins) for sic in sic_codes]


    return np.divide(covariances, totals ** 2)

def load_means():
    means = {}
    with open('parameters.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        means = next(reader)

    return means

def load_covariances():
    means = {}
    with open('parameters.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        means = next(reader)
        covariances = next(reader)

    return covariances

def la_covariance(i, la, max_age, local_authorities, sic_codes, age_bins, means):
    s = 0
    sic_vectors = []
    print(la)
    for sic in sic_codes:
        sic_index = sic_codes.index(sic)
        ages = np.zeros(max_age + 1)
        if sic in age_bins[la]:
            for age, n in age_bins[la][sic].items():
                ages[age] = n * (1 + means[i] + means[len(local_authorities) + sic_index]) ** age

        sic_vectors.append(ages)


    for j in range(len(sic_codes)):
        #print(j)
        s += np.sum(np.outer(sic_vectors[j], sic_vectors[j]))
        for k in range(j + 1, len(sic_codes)):
                s += 2 * np.sum(np.outer(sic_vectors[j], sic_vectors[k]))

    return s


def sic_covariance(i, sic, max_age, local_authorities, sic_codes, age_bins, means):
    s = 0
    print(sic)
    la_vectors = []
    for la in local_authorities:
        la_index = local_authorities.index(la)
        ages = np.zeros(max_age + 1)
        if sic in age_bins[la]:
            for age, n in age_bins[la][sic].items():
                ages[age] = n * (1 + means[la_index] + means[len(local_authorities) + i]) ** age
        la_vectors.append(ages)
    for j in range(len(local_authorities)):
        #print(j)
        s += np.sum(np.outer(la_vectors[j], la_vectors[j]))
        for k in range(j + 1, len(local_authorities)):
            s += 2 * np.sum(np.outer(la_vectors[j], la_vectors[k]))

    return s

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
                jacobian[la_index][la_index] += 2 * params[la_index] * size_deriv
                jacobian[number_of_local_authorities + sc_index][number_of_local_authorities + sc_index] += size_deriv

                jacobian[la_index][number_of_local_authorities + sc_index] += size_deriv
                jacobian[number_of_local_authorities + sc_index][la_index] += size_deriv

                totals[la_index] += n
                totals[number_of_local_authorities + sc_index] += n

    #print(jacobian)

    return np.divide(jacobian, totals)

def variance_jacobian(params, target, means, covariances, age_bins, local_authorities, sic_codes):
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

                jacobian[la_index][total_las + sic_index] += (n / totals_by_la[la]) * 2 * sic_param * d_var
                jacobian[total_las + sic_index][la_index] += (n / totals_by_sic[sic]) * 2 * la_param * d_var
                #jacobian[total_las + sic_index][la_index] += (n / totals_by_la[la]) * 2 * sic_param * d_var
                #jacobian[la_index][total_las + sic_index] += (n / totals_by_sic[sic]) * 2 * la_param * d_var


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

            #print(sic, mean, variance, mu, sigma)

            means[sic] = mean
            variances[sic] = variance
            #else:
            #    print(sic)


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

            #print(la, mean, variance, mu, sigma)



    return means, variances


def get_mean_varaince_of_lognorm(mu, sigma):
    return lognorm.mean(s = sigma, scale=np.exp(mu)), lognorm.var(s = sigma, scale=np.exp(mu))

if __name__ == '__main__':
    main()
