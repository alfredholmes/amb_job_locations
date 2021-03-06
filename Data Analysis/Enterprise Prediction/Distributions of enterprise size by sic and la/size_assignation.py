#load companies and get their local authority
#calculate the number with each SIC and in each local authority
#pull sizes from the distributions
import csv, datetime
import numpy as np
from scipy.stats import lognorm
import random

def main():
    print('loading companies...')
    companies = get_company_data(datetime.datetime(2017, 4, 1))
    print('picking random 500000 companies...')
    companies = [c for c in companies.values()]
    #print(len(companies))
    random.shuffle(companies)
    companies = companies[:500000]
    #companies = companies
    print('getting distribution data...')
    size_distributions_by_sic = get_size_distributions_by_sic()
    size_distributions_by_la  = get_size_distributions_by_la()
    sic_multipliers = get_sic_multipliers()


    las  = {}
    sics = {}

    print('processing data...')

    new_companies = []

    for i, company in enumerate(companies):
        la = company['la']
        sic  = company['sic']
        age = company['age']
        if sic not in sic_multipliers:
            continue

        if la not in size_distributions_by_la:
            continue

        if sic not in size_distributions_by_sic:
            continue

        multiplier = sic_multipliers[sic]

        if la in las:
            las[la] += multiplier
        else:
            las[la]  = multiplier

        if sic in sics:
            sics[sic] += multiplier
        else:
            sics[sic]  = multiplier

        base_multiplier = int(multiplier)
        additional_multiplier = multiplier - base_multiplier

        for _ in range(base_multiplier):
            new_companies.append({'la': la, 'sic': sic, 'age': age})
        if random.random() < additional_multiplier:
            new_companies.append({'la': la, 'sic': sic, 'age': age})

    print(len(new_companies))

    sizes_by_la  = {}
    sizes_by_sic = {}
    print('generating sizes...')
    for la, n in las.items():
        n = int(round(n))
        sizes_by_la[la] = sorted(lognorm.rvs(size_distributions_by_la[la]['sd'], scale=np.exp(size_distributions_by_la[la]['mean']), size=n))
    for sic, n in sics.items():
        n = int(round(n))
        sizes_by_sic[sic] = sorted(lognorm.rvs(size_distributions_by_sic[sic]['sd'], scale=np.exp(size_distributions_by_sic[sic]['mean']), size=n))




    print('matching sizes...')
    i = 0

    for company in new_companies:
        i += 1
        #if i % 10000 == 0:
        print(i)
        la = company['la']
        sic = company['sic']

        if sic not in sizes_by_sic or la not in sizes_by_la:
            continue
        try:
            la_index, sic_index = find_closest(sizes_by_la[la], sizes_by_sic[sic])
            company['size'] = int(round((sizes_by_la[la][la_index] + sizes_by_sic[sic][sic_index]) / 2))
            #print('size_things')
            del sizes_by_la[la][la_index]
            del sizes_by_sic[sic][sic_index]
        except:
            continue

    with open('output.csv', 'w') as csvfile:
        to_save = ['la', 'sic', 'size', 'age']
        writer = csv.writer(csvfile)

        for company in new_companies:
            if 'size' in company:
                writer.writerow([company[s] for s in to_save])

def find_closest(arr_1, arr_2):
    i, j = 0, 0
    prev_horizontal = False #as in i was last to increase
    min = np.inf
    min_pair = None
    while i < len(arr_1) and j < len(arr_2):
        distance = (arr_1[i] - arr_2[j]) ** 2
        if distance < min:
            min = distance
            min_pair = (i, j)
        if arr_1[i] < arr_2[j]:
            i += 1
            prev_horizontal = True
        else:
            j += 1
            prev_horizontal = False
    return min_pair


def get_company_data(date):
    files = ['../Data/CH/Company_Data/' + str(i) + '.csv' for i in range(7)]
    last_last_seen = datetime.datetime.strptime('2018-07-01', '%Y-%m-%d')
    companies = {}
    for file in files:
        with open(file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for line in reader:
                last_seen = datetime.datetime.strptime(line[3], '%Y-%m-%d')
                if not (last_seen == last_last_seen or (date - last_seen).days < 0):
                    continue
                incorporation_date = datetime.datetime.strptime(line[2], '%Y-%m-%d')
                if (date - incorporation_date).days < 0:
                    continue
                id = line[0]
                la = line[5]
                try:
                    sic = int(line[1][:2])
                except:
                    continue
                if sic == 99:
                    continue
                age = date - incorporation_date
                companies[id] = {'la': la, 'sic': sic, 'age': age}

    return companies

def get_size_distributions_by_sic():
    params = {}
    with open('../Data/2017_2_sic_enterprise_lognormal_params.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for line in reader:
            if float(line[1]) == 0 and float(line[2]) == 1:
                continue
            if float(line[2]) > 50:
                continue
            params[int(line[0])] = {'mean': float(line[1]), 'sd': float(line[2])}
    return params

def get_size_distributions_by_la():
    params = {}
    with open('../Data/2017_la_enterprise_lognormal_params.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for line in reader:
            params[line[0]] = {'mean': float(line[1]), 'sd': float(line[2])}

    return params

def get_sic_multipliers():
    multipliers = {}
    with open('../Data/sic_ch_multipliers.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for line in reader:
            multipliers[int(line[0])] = float(line[1])

    return multipliers
if __name__ == '__main__':
    main()
