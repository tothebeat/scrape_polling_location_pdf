import csv
import re
import sys

output_file = 'polling_locations.csv'
deduplicated_csv_file = 'polling_locations-deduplicated.csv'

if len(sys.argv) < 2:
    print '''Syntax:

python %s <html file>

This will output to '%s' and '%s'.
    ''' % (__file__, output_file, deduplicated_csv_file)
    sys.exit(1)

with open(sys.argv[1], 'rb') as f:
    lines = f.read().split('\n')

br_lines = filter(lambda line: '<br>' in line, lines)

data = []
record_data = False
for line in br_lines:
    # start of section:
    # beginning of line is 'Polling Places'
    # end of section:
    # line after end of data starts with '* '
    if re.search('^Polling Place', line):
        record_data = True
        continue
    if re.search('^\* ', line):
        record_data = False
        continue
    if record_data:
        data.append(line)

# Strip the <br> html tag from all lines
stripped_lines = map(lambda line: re.search(r'(?P<text>.*)<br>', line).groupdict()['text'], data)

# Each line of data is comprised of four lines in this array
# 1. ward
# 2. precinct
# 3. name of polling location
# 4. polling location address
locations = []
for starting_index in range(0, len(stripped_lines), 4):
    location = dict(zip(['ward', 'precinct', 'name', 'address'], stripped_lines[starting_index:starting_index+4]))
    locations.append(location)

# in the translation from PDF to HTML, the column between precinct and location name is either blank or contains an x,
# with the presence of an x indicating that the location is NOT handicapped accessible.
for i, location in enumerate(locations):
    if re.search(r'^x ', location['name']):
        locations[i]['accessible'] = False
        locations[i]['name'] = re.search(r'^x (?P<name>.*)', locations[i]['name']).groupdict()['name']
    else:
        locations[i]['accessible'] = True

# Add on the city and state to the location address with the intention of being geocoded for display on a map
for i, location in enumerate(locations):
    location['address'] += ', Chicago, IL'

# Create our output CSV file
with open(output_file, 'wb') as f:
    dict_writer = csv.DictWriter(f, fieldnames=['ward', 'precinct', 'name', 'address', 'accessible'])
    dict_writer.writeheader()
    dict_writer.writerows(locations)

# It turns out that some locations appear multiple times, they serve as the polling place for several precincts
# in the same ward. We'll also create a CSV that has a de-duplicated list of locations along with the wards and
# precincts they represent.
addresses_hash = {}
for location in locations:
    ward = location['ward']
    precinct = location['precinct']
    ward_precinct = 'ward %s precinct %s' % (ward, precinct)
    name = location['name']
    address = location['address']
    accessible = location['accessible']
    if address not in addresses_hash:
        addresses_hash[address] = dict(accessible=accessible, name=name, address=address, wards_precincts=[ward_precinct])
    else:
        addresses_hash[address]['wards_precincts'].append(ward_precinct)

for address, record in addresses_hash.iteritems():
    addresses_hash[address]['wards_precincts'] = ', '.join(addresses_hash[address]['wards_precincts'])

# Write these de-duplicated polling locations to a separate CSV file
with open(deduplicated_csv_file, 'wb') as f:
    dict_writer = csv.DictWriter(f, fieldnames=['name', 'address', 'accessible', 'wards_precincts'])
    dict_writer.writeheader()
    dict_writer.writerows(addresses_hash.values())