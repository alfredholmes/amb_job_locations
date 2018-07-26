import csv, json, requests, re, time

# TODO: Error Logs

def main():
    #load post code data
    print('Loading Postcode data...')
    pc = PostCode()
    print('Done')
    #load CompanyNumber array
    print('Loading Company Numbers...')
    company_numbers = get_company_numbers()
    print('Done')
    n = 100
    i = 0
    #loop through the compnies, get the filing history and find location changes and staff changes, and write this to a file after n iterations
    last_request = 0
    data = []
    for company in company_numbers:
        i += 1
        print('Company ' + str(i) + ' ' + company)
        filing_history, last_request = get_company_filing_history(company, last_request)
        #get address and people changes
        moves, last_request = parse_filing_history(filing_history, company, last_request, pc)
        data += moves
        if i % 100 == 0:
            write_data(data)
            data = []

def write_data(data):
    with open('company_migration_data.csv', 'a') as csvfile:
        fields = ['Company Number', 'Date', 'Registered Staff', 'Old Postcode', 'New Postcode', 'Old Local Authority', 'New Local Authority']
        writer = csv.DictWriter(csvfile, fields)
        for line in data:
            if csvfile.tell() == 0:
                writer.writeheader()
            writer.writerow(line)

def get_company_numbers():
    numbers = []
    with open('CompanyNumbers2012-2018.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for line in reader:
            numbers.append(line[0])

    return numbers

def get_company_filing_history(company, last_request_time):
    index = 0
    fh = []
    while True:
        wait_until_difference(0.5, last_request_time)
        req = requests.get('https://api.companieshouse.gov.uk/company/' + company + '/filing-history', data={'items_per_page': 100, 'start_index': index}, auth=('evHt9MOd08fueWenYhMHXCf5SFO98vSiKuP-66tI', ''))
        last_request_time = time.time()
        if req.status_code != 200:
            print('Error with request: ' + req.status_code + req.text)
            return None, last_request_time

        available_files = json.loads(req.text)['total_count']

        if available_files <= 0:
            return fh, last_request_time
        else:
            fh = fh + json.loads(req.text)['items']

        if len(fh) >= json.loads(req.text)['total_count']:
            return fh, last_request_time
        index += 100

def wait_until_difference(difference, last_request):
    if time.time() - last_request < difference:
        #time.sleep(difference - (time.time() - last_request))
        pass

def parse_filing_history(filing_history, company, last_request, pc):
    #get the current address
    current_postcode = None
    for event in filing_history:
        if event['category'] == 'address':
            if 'description_values' in event and 'new_address' in event['description_values']:
                current_postcode = PostCode.postcode_from_address(event['description_values']['new_address'])
            else:
                #get the address through an extra request :(
                wait_until_difference(0.5, last_request)
                last_request = time.time()
                # TODO: Handle potential errors
                address = json.loads(requests.get('https://api.companieshouse.gov.uk/company/' + company + '/registered-office-address', auth=('evHt9MOd08fueWenYhMHXCf5SFO98vSiKuP-66tI', '')).text)
                current_postcode = PostCode.postcode_from_address(address['postal_code'])
            break

    #reverse the filing history array such that the array is in chronological order

    filing_history.reverse()
    moves = []
    # TODO: Verify that companies start with 1 staff member
    staff  = 1
    files = 0
    staff_at_date = {}
    files_at_date = {}
    for event in filing_history:
        files += 1
        if event['category'] == 'address':
            postcode = None
            if 'description' in event and event['description'] == 'legacy':
                postcode = PostCode.postcode_from_address(event['description_values']['description'])
            elif 'type' in event and event['type'] == 'AD01':
                postcode = PostCode.postcode_from_address(event['description_values']['old_address'])
            if postcode is not None:
                moves.append({'date': event['date'], 'moving_from': postcode})
        if event['category'] == 'officers':
            if 'description' in event and event['description'] == 'legacy':
                parts = event['description_values']['description'].lower().split(';')
                for part in parts:
                    if 'new' in part or 'appointed' in part:
                        staff += 1
                    if 'terminated' in part or 'resigned' in part:
                        staff -= 1

        if event['category'] == 'persons-with-significant-control':
            if event['subcategory'] == 'register' or event['subcategory'] == 'notifications':
                staff += 1
            if event['subcategory'] == 'termination':
                staff -= 1
        if staff < 1:
            staff = 1

        staff_at_date[event['date']] = staff
        files_at_date[event['date']] = files

    #sort out return
    r = []
    for i in range(0, len(moves)):
        r.append({
            'Company Number': company,
            'Date': moves[i]['date'],
            'Registered Staff': staff_at_date[moves[i]['date']],
            'Old Postcode': moves[i]['moving_from'],
            'New Postcode': current_postcode if i == len(moves) - 1 else moves[i + 1]['moving_from'],
            'Old Local Authority': pc.get_local_authority_from_postcode(moves[i]['moving_from']),
            'New Local Authority': pc.get_local_authority_from_postcode(current_postcode if i == len(moves) - 1 else moves[i + 1]['moving_from'])
        })
    return r, last_request



class PostCode:
    def __init__(self):
        with open('postcode_la.csv', 'r') as csvfile:
            self.postcode_local_authority = {}
            reader = csv.reader(csvfile)
            for line in reader:
                self.postcode_local_authority[line[0]] = line[1]

    def get_local_authority_form_address(self, address):
        s = PostCode.postcode_from_address(address)
        self.get_local_authority_from_postcode(s)

    def get_local_authority_from_postcode(self, postcode):
        if postcode is None:
            print('Error parsing postcode is None')
            return None

        if postcode in self.postcode_local_authority:
            return self.postcode_local_authority[postcode]
        else:
            print('Postcode not recognised: ' + postcode)
            return None

    def postcode_from_address(address):
        try:
            s = re.search(r'([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9]?[A-Za-z]))))\s?[0-9][A-Za-z]{2})', address.upper()).group(0)
        except:
            print('Error getting poscode from address: ' + address)
            return None
        #split and remove spaces
        s = s.split(' ')
        s = [a for a in s if len(a) > 0]
        if len(s) != 2:
            if len(s) == 1:
                return s[0][:-3] + " " + s[0][-3:]
            return None
        else:
            return s[0] + " " + s[1]





if __name__ == '__main__':
    main()